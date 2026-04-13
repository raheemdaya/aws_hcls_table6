"""Integration tests for the BMR Digitization Pipeline.

End-to-end tests that wire together all real components (with mock LLM)
and exercise the full pipeline flow.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.extraction import MockExtractionModel
from bmr_pipeline.feedback import FeedbackLoop
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.models import FieldStatus, RecordStatus
from bmr_pipeline.orchestrator import PipelineOrchestrator
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.scoring import MockConfidenceScorer


def _build_orchestrator(base_dir: Path) -> PipelineOrchestrator:
    """Create a fully-wired PipelineOrchestrator backed by *base_dir*."""
    return PipelineOrchestrator(
        validator=InputValidator(),
        assembler=PageAssembler(),
        extractor=MockExtractionModel(),
        scorer=MockConfidenceScorer(),
        store=RecordStore(storage_dir=base_dir / "records"),
        queue=ReExtractionQueue(queue_dir=base_dir / "queue"),
        feedback=FeedbackLoop(training_dir=base_dir / "training"),
    )


def test_end_to_end_pipeline_flow() -> None:
    """Integration: ingest → assemble → extract → score → review → persist.

    Validates Requirements 1.1–1.4, 2.1–2.4, 3.1–3.5, 4.1–4.4, 7.1–7.4.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        orchestrator = _build_orchestrator(tmp_path)

        # 1. Create temp files with supported extensions (PNG, PDF)
        png_file = tmp_path / "page1.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        pdf_file = tmp_path / "page2.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content for testing")

        # 2. Run the full pipeline
        record = orchestrator.process([png_file, pdf_file])

        # 3. Assert correct number of pages
        assert len(record.pages) == 2, f"Expected 2 pages, got {len(record.pages)}"
        assert record.pages[0].page_number == 1
        assert record.pages[1].page_number == 2

        # 4. Assert extracted fields with confidence scores
        assert len(record.current_fields) > 0, "Expected extracted fields"
        for field in record.current_fields:
            assert 0.0 <= field.confidence <= 1.0, (
                f"Field '{field.name}' confidence {field.confidence} out of [0, 1]"
            )

        # 5. Assert status is not FAILED
        assert record.status != RecordStatus.FAILED

        # 6. Simulate review: approve all fields
        record.approve_all_fields()
        for field in record.current_fields:
            assert field.status == FieldStatus.APPROVED, (
                f"Field '{field.name}' should be APPROVED after approve_all_fields()"
            )

        # 7. Save the approved record
        store = RecordStore(storage_dir=tmp_path / "records")
        store.save(record)

        # 8. Verify the record can be loaded back
        loaded = store.load(record.id)

        # 9. Verify loaded record matches saved one
        assert loaded.id == record.id
        assert loaded.status == record.status
        assert len(loaded.pages) == len(record.pages)
        assert len(loaded.current_fields) == len(record.current_fields)

        for orig, loaded_f in zip(record.current_fields, loaded.current_fields):
            assert orig.name == loaded_f.name
            assert orig.value == loaded_f.value
            assert orig.confidence == loaded_f.confidence
            assert orig.status == loaded_f.status


def test_reextraction_flow() -> None:
    """Integration: flag → queue → re-extract → verify history preserved.

    Validates Requirements 6.1–6.4.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        orchestrator = _build_orchestrator(tmp_path)

        # 1. Create a temp file and process it through the pipeline
        png_file = tmp_path / "page1.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

        record = orchestrator.process([png_file])
        original_fields = list(record.current_fields)
        assert len(original_fields) > 0, "Initial extraction should produce fields"
        assert len(record.extraction_history) == 0, "No history before re-extraction"

        # 2. Flag the record for re-extraction by enqueuing with reviewer notes
        reviewer_notes = "Field 'batch_id' looks incorrect, please re-check"
        queue = ReExtractionQueue(queue_dir=tmp_path / "queue")
        queue.enqueue(record.id, reviewer_notes)

        # 3. Call process_reextraction()
        updated_record = orchestrator.process_reextraction(record.id)

        # 4. Assert extraction_history has 1 entry (the previous extraction)
        assert len(updated_record.extraction_history) == 1, (
            f"Expected 1 history entry, got {len(updated_record.extraction_history)}"
        )

        # 5. Assert current_fields are updated with new extraction
        assert len(updated_record.current_fields) > 0, "Re-extraction should produce fields"
        for field in updated_record.current_fields:
            assert 0.0 <= field.confidence <= 1.0, (
                f"Field '{field.name}' confidence {field.confidence} out of [0, 1]"
            )

        # 6. Assert the reviewer notes are preserved in the history entry
        history_entry = updated_record.extraction_history[0]
        assert history_entry.reviewer_notes == reviewer_notes, (
            f"Expected reviewer notes '{reviewer_notes}', got '{history_entry.reviewer_notes}'"
        )
        assert history_entry.attempt_number == 1
        assert len(history_entry.fields) == len(original_fields), (
            "History entry should preserve the original fields"
        )

        # 7. Verify the record is saved and can be loaded back
        store = RecordStore(storage_dir=tmp_path / "records")
        loaded = store.load(updated_record.id)

        assert loaded.id == updated_record.id
        assert len(loaded.extraction_history) == 1
        assert loaded.extraction_history[0].reviewer_notes == reviewer_notes
        assert len(loaded.current_fields) == len(updated_record.current_fields)


def test_feedback_loop_persist_train_retrain() -> None:
    """Integration: persist → training dataset → retrain trigger.

    Validates Requirements 8.1–8.4.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Use a low retrain threshold so we can trigger it easily
        orchestrator = PipelineOrchestrator(
            validator=InputValidator(),
            assembler=PageAssembler(),
            extractor=MockExtractionModel(),
            scorer=MockConfidenceScorer(),
            store=RecordStore(storage_dir=tmp_path / "records"),
            queue=ReExtractionQueue(queue_dir=tmp_path / "queue"),
            feedback=FeedbackLoop(
                training_dir=tmp_path / "training", retrain_threshold=2
            ),
        )
        feedback = orchestrator._feedback
        training_dir = tmp_path / "training"

        # --- Record 1 ---
        png1 = tmp_path / "page1.png"
        png1.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        record1 = orchestrator.process([png1])
        record1.approve_all_fields()

        # Add validated record to feedback loop (Req 8.1, 8.2)
        feedback.add_validated_record(record1)

        # Verify the record was saved in the training directory
        training_file1 = training_dir / f"{record1.id}.json"
        assert training_file1.exists(), "Record 1 should be persisted in training dir"

        # Not enough records yet – should_retrain should be False
        assert not feedback.should_retrain(), (
            "should_retrain() should be False with only 1 record (threshold=2)"
        )

        # --- Record 2 ---
        png2 = tmp_path / "page2.png"
        png2.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        record2 = orchestrator.process([png2])
        record2.approve_all_fields()

        feedback.add_validated_record(record2)

        training_file2 = training_dir / f"{record2.id}.json"
        assert training_file2.exists(), "Record 2 should be persisted in training dir"

        # Threshold met – should_retrain should be True (Req 8.3)
        assert feedback.should_retrain(), (
            "should_retrain() should be True after 2 records (threshold=2)"
        )

        # Trigger retrain and verify the event (Req 8.3, 8.4)
        event = feedback.trigger_retrain()
        assert event.records_added == 2, (
            f"Expected 2 records_added, got {event.records_added}"
        )
        assert event.total_training_records == 2, (
            f"Expected 2 total_training_records, got {event.total_training_records}"
        )
        assert event.timestamp is not None

        # Counter should reset after trigger_retrain (Req 8.3)
        assert not feedback.should_retrain(), (
            "should_retrain() should be False after trigger_retrain() resets counter"
        )
