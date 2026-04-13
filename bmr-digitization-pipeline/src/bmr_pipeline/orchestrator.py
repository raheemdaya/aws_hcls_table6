"""Pipeline orchestration for the BMR Digitization Pipeline.

Coordinates the full pipeline flow: validate → assemble → extract → score → store.
Handles re-extraction from the queue with reviewer notes as context.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.extraction import ExtractionModel
from bmr_pipeline.feedback import FeedbackLoop
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.models import (
    ExtractionAttempt,
    ExtractionError,
    Record,
    RecordStatus,
)
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.scoring import ConfidenceScorer


class PipelineOrchestrator:
    """Coordinates the full BMR digitization pipeline.

    Wires together: InputValidator → PageAssembler → ExtractionModel →
    ConfidenceScorer → RecordStore, and handles re-extraction from the queue.
    """

    def __init__(
        self,
        validator: InputValidator,
        assembler: PageAssembler,
        extractor: ExtractionModel,
        scorer: ConfidenceScorer,
        store: RecordStore,
        queue: ReExtractionQueue,
        feedback: FeedbackLoop,
    ) -> None:
        self._validator = validator
        self._assembler = assembler
        self._extractor = extractor
        self._scorer = scorer
        self._store = store
        self._queue = queue
        self._feedback = feedback

    def process(self, file_paths: list[Path]) -> Record:
        """Run the full pipeline on a list of input files.

        Flow:
        1. Validate each file using InputValidator.
        2. Assemble validated pages into a Record using PageAssembler.
        3. Extract fields using ExtractionModel.
        4. If extraction fails, set record status to FAILED and save.
        5. Score fields using ConfidenceScorer and update field confidences.
        6. Save the record using RecordStore.
        7. Return the record.
        """
        # 1. Validate
        validated_pages = [self._validator.validate(fp) for fp in file_paths]

        # 2. Assemble
        record = self._assembler.assemble(validated_pages)

        # 3. Extract
        try:
            extraction_result = self._extractor.extract(record)
        except ExtractionError:
            # 4. Failed extraction → mark FAILED and persist
            record.status = RecordStatus.FAILED
            record.updated_at = datetime.utcnow()
            self._store.save(record)
            return record

        # Update record with extraction results
        record.current_fields = extraction_result.fields
        record.inferred_schema = extraction_result.inferred_schema

        # 5. Score fields and update confidences
        scores = self._scorer.score(record, extraction_result)
        score_map = {s.field_name: s.confidence for s in scores}
        for field in record.current_fields:
            if field.name in score_map:
                field.confidence = score_map[field.name]

        record.updated_at = datetime.utcnow()

        # 6. Save
        self._store.save(record)

        # 7. Return
        return record

    def process_reextraction(self, record_id: str) -> Record:
        """Re-extract a flagged record using reviewer notes as context.

        Flow:
        1. Dequeue from ReExtractionQueue to get reviewer_notes.
        2. Load the record from RecordStore.
        3. Snapshot current fields into extraction_history.
        4. Extract with reviewer notes as context.
        5. Update current_fields with new extraction results.
        6. Score new fields.
        7. Save and return the updated record.
        """
        # 1. Dequeue
        item = self._queue.dequeue()
        if item is None:
            # Nothing in queue – just load and return the record as-is
            return self._store.load(record_id)

        _dequeued_id, reviewer_notes = item

        # 2. Load
        record = self._store.load(record_id)

        # 3. Preserve current fields in extraction history
        attempt_number = len(record.extraction_history) + 1
        previous_attempt = ExtractionAttempt(
            attempt_number=attempt_number,
            timestamp=datetime.utcnow(),
            fields=list(record.current_fields),
            reviewer_notes=reviewer_notes,
            model_id="previous",
        )
        record.extraction_history.append(previous_attempt)

        # 4. Re-extract with reviewer notes as context
        extraction_result = self._extractor.extract(record, context=reviewer_notes)

        # 5. Update current fields
        record.current_fields = extraction_result.fields
        record.inferred_schema = extraction_result.inferred_schema

        # 6. Score new fields
        scores = self._scorer.score(record, extraction_result)
        score_map = {s.field_name: s.confidence for s in scores}
        for field in record.current_fields:
            if field.name in score_map:
                field.confidence = score_map[field.name]

        record.updated_at = datetime.utcnow()

        # 7. Save and return
        self._store.save(record)
        return record
