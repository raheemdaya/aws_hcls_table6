"""Amazon Bedrock (Claude) extraction model for the BMR Digitization Pipeline.

Uses Claude's vision capabilities via the Bedrock Converse API to extract
structured fields from scanned BMR pages (images and PDFs).
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import boto3

from bmr_pipeline.models import (
    ExtractionError,
    ExtractionResult,
    ExtractedField,
    FieldStatus,
    Record,
)

logger = logging.getLogger(__name__)

# Media types recognised by Bedrock Converse
_EXT_TO_MEDIA = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
}

_SYSTEM_PROMPT = """\
You are a document extraction specialist for pharmaceutical Batch Manufacturing Records (BMRs).

Given scanned page(s) of a handwritten BMR, extract ALL fields you can identify into a flat
JSON object. Each key is the field name (snake_case) and each value is the text you read.

Rules:
- Infer the schema from the document — do NOT use a hardcoded list of fields.
- Include every distinct piece of data you can read (batch numbers, dates, product names,
  quantities, operator names, equipment IDs, test results, etc.).
- If a value is illegible, set it to null.
- Return ONLY valid JSON — no markdown fences, no commentary.
"""


class BedrockExtractionModel:
    """Extract structured fields from BMR pages using Claude on Amazon Bedrock."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name: str = "us-east-1",
    ) -> None:
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region_name)

    @property
    def MODEL_ID(self) -> str:  # noqa: N802 – matches MockExtractionModel interface
        return self._model_id

    # ------------------------------------------------------------------
    # ExtractionModel protocol
    # ------------------------------------------------------------------

    def extract(self, record: Record, context: str | None = None) -> ExtractionResult:
        if not record.pages:
            raise ExtractionError("No pages in record to extract from")

        content_blocks = self._build_content_blocks(record, context)
        raw_json = self._call_bedrock(content_blocks)
        return self._parse_response(raw_json)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_content_blocks(
        self, record: Record, context: str | None
    ) -> list[dict]:
        """Build the Converse API content blocks from record pages."""
        blocks: list[dict] = []

        for page in record.pages:
            path = Path(page.file_path)
            ext = path.suffix.lstrip(".").lower()
            media_type = _EXT_TO_MEDIA.get(ext)
            if media_type is None:
                continue

            data = path.read_bytes()

            if media_type == "application/pdf":
                blocks.append({
                    "document": {
                        "format": "pdf",
                        "name": path.stem.replace(" ", "_")[:40],
                        "source": {"bytes": data},
                    }
                })
            else:
                blocks.append({
                    "image": {
                        "format": ext if ext in ("png", "jpeg", "gif", "webp") else "png",
                        "source": {"bytes": data},
                    }
                })

        prompt = "Extract all fields from the scanned BMR page(s) above as a flat JSON object."
        if context:
            prompt += f"\n\nReviewer notes from a previous pass: {context}"

        blocks.append({"text": prompt})
        return blocks

    def _call_bedrock(self, content_blocks: list[dict]) -> str:
        """Send the request to Bedrock Converse and return the text response."""
        try:
            response = self._client.converse(
                modelId=self._model_id,
                system=[{"text": _SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": content_blocks}],
                inferenceConfig={"maxTokens": 4096, "temperature": 0.0},
            )
            # Extract text from the response
            output = response["output"]["message"]["content"]
            text_parts = [block["text"] for block in output if "text" in block]
            return "\n".join(text_parts)
        except Exception as exc:
            raise ExtractionError(f"Bedrock API call failed: {exc}") from exc

    def _parse_response(self, raw: str) -> ExtractionResult:
        """Parse the JSON response from Claude into an ExtractionResult."""
        # Strip markdown fences if Claude included them despite instructions
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ExtractionError(
                f"Failed to parse extraction JSON: {exc}\nRaw response: {raw[:500]}"
            ) from exc

        if not isinstance(data, dict):
            raise ExtractionError(f"Expected JSON object, got {type(data).__name__}")

        fields = []
        schema_fields = {}
        for key, value in data.items():
            fields.append(
                ExtractedField(
                    name=key,
                    value=str(value) if value is not None else None,
                    confidence=0.0,
                    status=FieldStatus.PENDING,
                )
            )
            schema_fields[key] = {
                "type": "string" if isinstance(value, str) else type(value).__name__,
                "description": f"Extracted field: {key}",
            }

        return ExtractionResult(
            fields=fields,
            inferred_schema={"fields": schema_fields},
            model_id=self._model_id,
        )
