"""Unit tests for ExtractionModel protocol and MockExtractionModel."""

import pytest

from bmr_pipeline.extraction import ExtractionModel, MockExtractionModel
from bmr_pipeline.models import (
    ExtractionError,
    ExtractionResult,
    PageImage,
    Record,
)


# --- Helpers ---


def _record_with_pages(n: int = 1) -> Record:
    """Create a Record with *n* pages for testing."""
    pages = [
        PageImage(
            page_number=i + 1,
            file_path=f"/scans/page{i + 1}.png",
            original_filename=f"page{i + 1}.png",
        )
        for i in range(n)
    ]
    return Record(pages=pages)


# --- A second mock implementation to prove the protocol is provider-agnostic ---


class AlternativeMockExtractionModel:
    """A different mock that also satisfies the ExtractionModel protocol."""

    MODEL_ID = "alt-mock-v1"

    def extract(self, record: Record, context: str | None = None) -> ExtractionResult:
        if not record.pages:
            raise ExtractionError("Empty record")
        from bmr_pipeline.models import ExtractedField, FieldStatus

        fields = [
            ExtractedField(
                name="lot_number",
                value="LOT-999",
                confidence=0.0,
                status=FieldStatus.PENDING,
            ),
        ]
        return ExtractionResult(
            fields=fields,
            inferred_schema={"fields": {"lot_number": {"type": "string"}}},
            model_id=self.MODEL_ID,
        )


# --- Unit Tests ---


def test_mock_extraction_returns_valid_result() -> None:
    """MockExtractionModel.extract() returns an ExtractionResult with fields,
    inferred_schema, and model_id.

    **Validates: Requirements 3.4, 3.5**
    """
    record = _record_with_pages(2)
    result = MockExtractionModel().extract(record)

    assert isinstance(result, ExtractionResult)
    assert len(result.fields) > 0
    assert isinstance(result.inferred_schema, dict)
    assert result.model_id == MockExtractionModel.MODEL_ID


def test_provider_agnostic_interface() -> None:
    """Multiple implementations satisfy the ExtractionModel protocol and can be
    used interchangeably through the same interface.

    **Validates: Requirements 3.4**
    """
    record = _record_with_pages(1)

    models: list[ExtractionModel] = [
        MockExtractionModel(),
        AlternativeMockExtractionModel(),
    ]

    for model in models:
        # Runtime protocol check
        assert isinstance(model, ExtractionModel)

        result = model.extract(record)
        assert isinstance(result, ExtractionResult)
        assert len(result.fields) > 0
        assert isinstance(result.inferred_schema, dict)
        assert isinstance(result.model_id, str)


def test_failed_extraction_on_empty_record() -> None:
    """Extracting from a Record with no pages raises ExtractionError.

    **Validates: Requirements 3.5**
    """
    empty_record = Record(pages=[])

    with pytest.raises(ExtractionError):
        MockExtractionModel().extract(empty_record)
