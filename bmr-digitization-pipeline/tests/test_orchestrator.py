"""Property-based tests for PipelineOrchestrator re-extraction behaviour."""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.extraction import MockExtractionModel
from bmr_pipeline.feedback import FeedbackLoop
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.orchestrator import PipelineOrchestrator
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.scoring import MockConfidenceScorer


def _build_orchestrator(base_dir: Path) -> PipelineOrchestrator:
    """Create a PipelineOrchestrator wired to real components backed by *base_dir*."""
    records_dir = base_dir / "records"
    queue_dir = base_dir / "queue"
    training_dir = base_dir / "training"

    return PipelineOrchestrator(
        validator=InputValidator(),
        assembler=PageAssembler(),
        extractor=MockExtractionModel(),
        scorer=MockConfidenceScorer(),
        store=RecordStore(storage_dir=records_dir),
        queue=ReExtractionQueue(queue_dir=queue_dir),
        feedback=FeedbackLoop(training_dir=training_dir),
    )


# Feature: bmr-digitization-pipeline, Property 8: Re-extraction updates current fields and preserves full history
@settings(max_examples=100)
@given(num_rounds=st.integers(min_value=1, max_value=5))
def test_reextraction_preserves_history_and_updates_fields(
    num_rounds: int,
) -> None:
    """
    Property 8: Re-extraction updates current fields and preserves full history.

    For any Record that has undergone N extraction attempts, after a
    re-extraction the Record SHALL have N+1 entries in its extraction
    history, the current fields SHALL reflect the latest extraction, and
    all previous attempts SHALL be preserved unchanged.

    **Validates: Requirements 6.3, 6.4**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        orchestrator = _build_orchestrator(tmp_path)

        # Create a real temp file with a supported extension for InputValidator
        input_file = tmp_path / "page1.png"
        input_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        # Initial processing — creates the record with current_fields but no history
        record = orchestrator.process([input_file])
        assert len(record.current_fields) > 0, "Initial extraction must produce fields"
        assert len(record.extraction_history) == 0, "Fresh record has no history yet"

        # Track history snapshots so we can verify they stay unchanged
        history_snapshots: list[list[dict]] = []

        for round_idx in range(num_rounds):
            previous_history_len = len(record.extraction_history)

            # Enqueue the record for re-extraction with reviewer notes
            orchestrator._queue.enqueue(
                record.id,
                f"Please re-check fields — round {round_idx + 1}",
            )

            # Perform re-extraction
            record = orchestrator.process_reextraction(record.id)

            # --- Assertion 1: history length increased by exactly 1 ---
            assert len(record.extraction_history) == previous_history_len + 1, (
                f"Round {round_idx + 1}: expected history length "
                f"{previous_history_len + 1}, got {len(record.extraction_history)}"
            )

            # --- Assertion 2: current_fields reflect the latest extraction ---
            assert len(record.current_fields) > 0, (
                f"Round {round_idx + 1}: current_fields should not be empty after re-extraction"
            )

            # --- Assertion 3: all previous history entries are preserved unchanged ---
            for snap_idx, expected_snap in enumerate(history_snapshots):
                actual = [f.model_dump() for f in record.extraction_history[snap_idx].fields]
                assert actual == expected_snap, (
                    f"Round {round_idx + 1}: history entry {snap_idx} was mutated"
                )

            # Snapshot the newly added history entry for future rounds
            latest_entry = record.extraction_history[-1]
            history_snapshots.append([f.model_dump() for f in latest_entry.fields])


# ---------------------------------------------------------------------------
# Unit tests for PipelineOrchestrator (Task 12.3)
# ---------------------------------------------------------------------------

import os

from bmr_pipeline.models import ExtractionError, RecordStatus


def test_end_to_end_pipeline_with_mock_llm() -> None:
    """End-to-end pipeline: validate → assemble → extract → score → store.

    Creates temporary files with supported extensions, runs process(), and
    asserts the returned record has current_fields, confidence scores, and
    is persisted in the store.

    **Validates: Requirements 3.5**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        orchestrator = _build_orchestrator(tmp_path)

        # Create temp files with supported extensions
        png_file = tmp_path / "page1.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        pdf_file = tmp_path / "page2.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content for testing")

        record = orchestrator.process([png_file, pdf_file])

        # Record should have extracted fields
        assert len(record.current_fields) > 0, "Expected extracted fields"

        # Every field should have a confidence score set by the scorer
        for field in record.current_fields:
            assert 0.0 <= field.confidence <= 1.0, (
                f"Field '{field.name}' confidence {field.confidence} out of range"
            )

        # Record should NOT be FAILED
        assert record.status != RecordStatus.FAILED

        # Record should be persisted in the store
        records_dir = tmp_path / "records"
        stored = orchestrator._store.load(record.id)
        assert stored.id == record.id
        assert len(stored.current_fields) == len(record.current_fields)


def test_failed_extraction_marks_record_as_failed() -> None:
    """When the ExtractionModel raises ExtractionError the record status is FAILED.

    **Validates: Requirements 3.5**
    """

    class _AlwaysFailExtractor:
        """ExtractionModel that always raises ExtractionError."""

        def extract(self, record, context=None):
            raise ExtractionError("Simulated extraction failure")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        records_dir = tmp_path / "records"
        queue_dir = tmp_path / "queue"
        training_dir = tmp_path / "training"

        orchestrator = PipelineOrchestrator(
            validator=InputValidator(),
            assembler=PageAssembler(),
            extractor=_AlwaysFailExtractor(),
            scorer=MockConfidenceScorer(),
            store=RecordStore(storage_dir=records_dir),
            queue=ReExtractionQueue(queue_dir=queue_dir),
            feedback=FeedbackLoop(training_dir=training_dir),
        )

        # Create a valid input file
        input_file = tmp_path / "page.png"
        input_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        record = orchestrator.process([input_file])

        # Record must be marked FAILED
        assert record.status == RecordStatus.FAILED

        # No current fields should be set (extraction failed before scoring)
        assert len(record.current_fields) == 0

        # Record should still be persisted
        stored = orchestrator._store.load(record.id)
        assert stored.status == RecordStatus.FAILED
