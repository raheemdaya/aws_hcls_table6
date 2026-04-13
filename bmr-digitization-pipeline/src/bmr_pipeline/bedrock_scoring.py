"""Amazon Bedrock (Claude) confidence scorer for the BMR Digitization Pipeline.

Uses Claude to judge the confidence of each extracted field by re-examining
the source pages.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import boto3

from bmr_pipeline.models import (
    ExtractionResult,
    FieldScore,
    Record,
)

logger = logging.getLogger(__name__)

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

_SCORING_PROMPT = """\
You are a quality reviewer for pharmaceutical Batch Manufacturing Records.

Given the scanned page(s) and the extracted fields below, assign a confidence
score between 0.0 and 1.0 to each field based on how confident you are the
extracted value is correct.

Scoring guide:
- 1.0: Clearly legible, unambiguous
- 0.7-0.9: Mostly legible, minor uncertainty
- 0.4-0.6: Partially legible or ambiguous
- 0.1-0.3: Mostly illegible, guessing
- 0.0: Cannot determine at all

Return ONLY a JSON object where keys are field names and values are floats.
No markdown fences, no commentary.
"""


class BedrockConfidenceScorer:
    """Score extracted fields using Claude on Amazon Bedrock."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        region_name: str = "us-east-1",
    ) -> None:
        self._model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region_name)

    def score(
        self, record: Record, extraction_result: ExtractionResult
    ) -> list[FieldScore]:
        try:
            return self._score_via_llm(record, extraction_result)
        except Exception as exc:
            logger.warning("Bedrock scoring failed, falling back to 0.0: %s", exc)
            return [
                FieldScore(field_name=f.name, confidence=0.0)
                for f in extraction_result.fields
            ]

    def _score_via_llm(
        self, record: Record, extraction_result: ExtractionResult
    ) -> list[FieldScore]:
        blocks: list[dict] = []

        # Add page images/documents
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

        # Add the extracted fields as context
        fields_dict = {f.name: f.value for f in extraction_result.fields}
        blocks.append({
            "text": (
                f"Extracted fields:\n{json.dumps(fields_dict, indent=2)}\n\n"
                "Score each field's confidence as described."
            )
        })

        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": _SCORING_PROMPT}],
            messages=[{"role": "user", "content": blocks}],
            inferenceConfig={"maxTokens": 2048, "temperature": 0.0},
        )

        output = response["output"]["message"]["content"]
        text = "\n".join(b["text"] for b in output if "text" in b)

        # Parse JSON
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        scores_dict = json.loads(cleaned)

        results = []
        for field in extraction_result.fields:
            conf = scores_dict.get(field.name, 0.0)
            conf = max(0.0, min(1.0, float(conf)))
            results.append(FieldScore(field_name=field.name, confidence=conf))

        return results
