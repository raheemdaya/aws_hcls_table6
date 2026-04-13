"""ExtractionModel protocol and mock implementation for the BMR Digitization Pipeline."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bmr_pipeline.models import (
    ExtractionError,
    ExtractionResult,
    ExtractedField,
    FieldStatus,
    Record,
)


@runtime_checkable
class ExtractionModel(Protocol):
    """Provider-agnostic interface for LLM-based extraction.

    Implementations wrap specific providers (OpenAI, Anthropic, local models, etc.)
    without requiring changes to the rest of the pipeline.
    """

    def extract(self, record: Record, context: str | None = None) -> ExtractionResult:
        """Extract structured fields from a Record's page images.

        Args:
            record: The assembled record with page images.
            context: Optional reviewer notes for re-extraction guidance.

        Returns:
            ExtractionResult with extracted fields and inferred schema.
        """
        ...


class MockExtractionModel:
    """Mock implementation of ExtractionModel for testing.

    Returns synthetic extracted fields and an inferred schema,
    simulating what a real LLM extraction would produce.
    """

    MODEL_ID = "mock-extraction-v1"

    def extract(self, record: Record, context: str | None = None) -> ExtractionResult:
        """Return synthetic extraction results for testing.

        Args:
            record: The assembled record with page images.
            context: Optional reviewer notes for re-extraction guidance.

        Returns:
            ExtractionResult with synthetic fields and inferred schema.

        Raises:
            ExtractionError: If the record has no pages.
        """
        if not record.pages:
            raise ExtractionError("No pages in record to extract from")

        fields = [
            ExtractedField(
                name="batch_number",
                value="BATCH-2024-001",
                confidence=0.0,
                status=FieldStatus.PENDING,
            ),
            ExtractedField(
                name="product_name",
                value="Aspirin 500mg Tablets",
                confidence=0.0,
                status=FieldStatus.PENDING,
            ),
            ExtractedField(
                name="date",
                value="2024-01-15",
                confidence=0.0,
                status=FieldStatus.PENDING,
            ),
            ExtractedField(
                name="operator",
                value="J. Smith",
                confidence=0.0,
                status=FieldStatus.PENDING,
            ),
        ]

        inferred_schema: dict = {
            "fields": {
                "batch_number": {"type": "string", "description": "Manufacturing batch identifier"},
                "product_name": {"type": "string", "description": "Name and dosage of the product"},
                "date": {"type": "string", "format": "date", "description": "Manufacturing date"},
                "operator": {"type": "string", "description": "Operator who performed the step"},
            },
        }

        if context is not None:
            inferred_schema["reviewer_context"] = context

        return ExtractionResult(
            fields=fields,
            inferred_schema=inferred_schema,
            model_id=self.MODEL_ID,
        )
