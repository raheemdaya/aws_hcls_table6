# Implementation Plan: BMR Digitization & Validation Pipeline

## Overview

Incremental implementation of the BMR digitization pipeline in Python. Each task builds on the previous, starting with project scaffolding and data models, then layering in pipeline components, and finishing with the Streamlit review UI and feedback loop. All code lives under `bmr-digitization-pipeline/`.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `bmr-digitization-pipeline/pyproject.toml` with dependencies: pydantic, streamlit, hypothesis, pytest, Pillow, PyPDF2
  - Create directory structure: `src/bmr_pipeline/`, `ui/`, `tests/`, `data/`, `storage/records/`, `storage/queue/`, `storage/training/`
  - Create `src/bmr_pipeline/__init__.py`, `tests/__init__.py`
  - Create `src/bmr_pipeline/config.py` with pipeline configuration (storage paths, supported formats, retrain threshold)
  - _Requirements: All_

- [x] 2. Implement data models and custom exceptions
  - [x] 2.1 Create Pydantic data models in `src/bmr_pipeline/models.py`
    - Implement all models: `FieldStatus`, `RecordStatus`, `ExtractedField`, `ExtractionAttempt`, `ReviewerAction`, `PageImage`, `Record`, `ExtractionResult`, `FieldScore`, `RetrainEvent`, `RecordSummary`, `ValidatedInput`
    - Implement `Record.approve_all_fields()` method that sets every field status to APPROVED
    - Implement custom exception hierarchy in `models.py`: `PipelineError`, `InputValidationError`, `AssemblyError`, `ExtractionError`, `ScoringError`, `PersistenceError`, `SchemaValidationError`
    - _Requirements: 1.1–1.4, 2.1–2.4, 3.1–3.5, 4.1–4.4, 5.3, 5.4, 6.3, 6.4, 7.2, 7.3, 9.1–9.4_

  - [x]* 2.2 Write property test: Record approval marks all fields approved
    - **Property 5: Record approval marks all fields approved**
    - **Validates: Requirements 5.3, 5.4**

  - [x]* 2.3 Write property test: Record IDs are unique
    - **Property 9: Unique record IDs**
    - **Validates: Requirements 7.3**

  - [x]* 2.4 Write property test: Record serialization round-trip
    - **Property 10: Record serialization round-trip**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 3. Implement InputValidator
  - [x] 3.1 Create `src/bmr_pipeline/input_validator.py`
    - Implement `InputValidator.validate(file_path)` that checks file extension against supported formats and verifies file readability
    - Raise `InputValidationError` for unsupported formats (include format name in message) and corrupted/unreadable files
    - Return `ValidatedInput` on success
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x]* 3.2 Write property test: Supported format acceptance
    - **Property 1: Supported format acceptance**
    - **Validates: Requirements 1.1, 1.2**

  - [x]* 3.3 Write property test: Unsupported format rejection
    - **Property 2: Unsupported format rejection**
    - **Validates: Requirements 1.3**

  - [x]* 3.4 Write unit tests for InputValidator
    - Test corrupted/unreadable file rejection
    - Test each supported format individually
    - _Requirements: 1.4_

- [ ] 4. Implement PageAssembler
  - [x] 4.1 Create `src/bmr_pipeline/assembler.py`
    - Implement `PageAssembler.assemble(pages, record_id)` that stitches validated pages into a single Record
    - Preserve page order and original image references
    - Raise `AssemblyError` on empty page list
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [-]* 4.2 Write property test: Assembly preserves page order and content
    - **Property 3: Assembly preserves page order and content**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [~]* 4.3 Write unit tests for PageAssembler
    - Test single-page assembly
    - Test empty page list error
    - _Requirements: 2.2, 2.4_

- [~] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement ExtractionModel protocol and mock implementation
  - [~] 6.1 Create `src/bmr_pipeline/extraction.py`
    - Define `ExtractionModel` Protocol with `extract(record, context)` method
    - Implement `MockExtractionModel` for testing that returns synthetic fields and inferred schema
    - Ensure the interface supports reviewer notes as context for re-extraction
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.2_

  - [~]* 6.2 Write unit tests for ExtractionModel
    - Test mock implementation returns valid ExtractionResult
    - Test provider-agnostic interface with multiple mock implementations
    - Test failed extraction returns error details
    - _Requirements: 3.4, 3.5_

- [ ] 7. Implement ConfidenceScorer protocol and mock implementation
  - [~] 7.1 Create `src/bmr_pipeline/scoring.py`
    - Define `ConfidenceScorer` Protocol with `score(record, extraction_result)` method
    - Implement `MockConfidenceScorer` for testing
    - Handle scoring failure by assigning 0.0 to failed fields
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [~]* 7.2 Write property test: Confidence scores are in valid range
    - **Property 4: Confidence scores are in valid range**
    - **Validates: Requirements 4.1, 4.3**

  - [~]* 7.3 Write unit tests for ConfidenceScorer
    - Test scorer configuration (same vs separate model)
    - Test scoring failure defaults to 0.0
    - _Requirements: 4.2, 4.4_

- [ ] 8. Implement RecordStore (JSON persistence)
  - [~] 8.1 Create `src/bmr_pipeline/record_store.py`
    - Implement `RecordStore` with `save(record)`, `load(record_id)`, `list_records()` methods
    - Persist records as JSON files in `storage/records/`
    - `list_records()` returns `RecordSummary` objects ordered by creation date descending
    - Raise `PersistenceError` on write failure, `SchemaValidationError` on invalid JSON deserialization
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 9.1, 9.2, 9.3, 9.4_

  - [~]* 8.2 Write property test: Records are listed in descending date order
    - **Property 6: Records listed in descending date order**
    - **Validates: Requirements 5.7**

  - [~]* 8.3 Write unit tests for RecordStore
    - Test write failure retains record for retry
    - Test invalid JSON deserialization error messages
    - _Requirements: 7.4, 9.4_

- [ ] 9. Implement ReExtractionQueue
  - [~] 9.1 Create `src/bmr_pipeline/queue.py`
    - Implement `ReExtractionQueue` with `enqueue(record_id, reviewer_notes)`, `dequeue()`, `pending()` methods
    - Persist queue items as JSON files in `storage/queue/`
    - _Requirements: 6.1_

  - [~]* 9.2 Write property test: Queue enqueue/dequeue preserves record ID and notes
    - **Property 7: Queue enqueue/dequeue preserves record ID and notes**
    - **Validates: Requirements 6.1**

- [~] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement FeedbackLoop
  - [~] 11.1 Create `src/bmr_pipeline/feedback.py`
    - Implement `FeedbackLoop` with `add_validated_record(record)`, `should_retrain()`, `trigger_retrain()` methods
    - Copy validated records to `storage/training/`
    - `should_retrain()` checks if new records exceed configurable threshold
    - `trigger_retrain()` returns `RetrainEvent` and logs the event
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [~]* 11.2 Write unit tests for FeedbackLoop
    - Test retraining trigger fires when threshold met
    - Test retraining trigger logging
    - _Requirements: 8.3, 8.4_

- [ ] 12. Implement PipelineOrchestrator
  - [~] 12.1 Create `src/bmr_pipeline/orchestrator.py`
    - Implement `PipelineOrchestrator` with `process(file_paths)` and `process_reextraction(record_id)` methods
    - Wire together: InputValidator → PageAssembler → ExtractionModel → ConfidenceScorer → RecordStore
    - `process_reextraction` reads from queue, passes reviewer notes as context, updates record with new extraction while preserving history
    - Handle failed extraction by setting Record status to FAILED
    - _Requirements: 1.1–1.4, 2.1–2.4, 3.1–3.5, 4.1–4.4, 6.1–6.4, 7.1–7.4_

  - [~]* 12.2 Write property test: Re-extraction updates current fields and preserves full history
    - **Property 8: Re-extraction updates current fields and preserves full history**
    - **Validates: Requirements 6.3, 6.4**

  - [~]* 12.3 Write unit tests for PipelineOrchestrator
    - Test end-to-end pipeline with mock LLM
    - Test failed extraction marks record as FAILED
    - _Requirements: 3.5_

- [ ] 13. Implement Streamlit Review UI
  - [~] 13.1 Create `ui/app.py` with Streamlit review interface
    - List records ordered by extraction date (most recent first) using RecordStore
    - Display extracted fields with color-coded confidence scores
    - Show original scanned page images alongside extracted data
    - Support inline editing of field values
    - Approve individual fields or entire records
    - Flag records for re-extraction with required reviewer notes (reject flag without notes)
    - On approval, trigger FeedbackLoop to add record to training dataset
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [~] 14. Implement synthetic data generator
  - Create `data/generate_synthetic.py` to produce sample BMR images for testing
  - Generate a small set of synthetic scanned pages in `data/sample_bmr/`
  - _Requirements: All (test data support)_

- [ ] 15. Write integration tests
  - [~]* 15.1 Write integration test: end-to-end pipeline flow
    - Test ingest → assemble → extract → score → review → persist with mock LLM
    - _Requirements: 1.1–1.4, 2.1–2.4, 3.1–3.5, 4.1–4.4, 7.1–7.4_

  - [~]* 15.2 Write integration test: re-extraction flow
    - Test flag → queue → re-extract → verify history preserved
    - _Requirements: 6.1–6.4_

  - [~]* 15.3 Write integration test: feedback loop
    - Test persist → training dataset → retrain trigger
    - _Requirements: 8.1–8.4_

- [~] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property-based tests use Hypothesis; unit tests use pytest
- All LLM interactions use mock implementations during testing
- Checkpoints ensure incremental validation throughout implementation
