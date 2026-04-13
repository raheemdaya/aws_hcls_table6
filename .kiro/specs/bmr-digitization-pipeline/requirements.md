# Requirements Document

## Introduction

This document defines the requirements for the BMR Digitization & Validation Pipeline — a system that digitizes handwritten Batch Manufacturing Records (BMRs) using AI-powered extraction, automated confidence scoring, and human-in-the-loop validation via a Streamlit review UI. Validated records are persisted locally as JSON and feed an active loop for continuous model improvement.

## Glossary

- **BMR**: A Batch Manufacturing Record — a handwritten document capturing manufacturing process data. A single BMR may span multiple scanned pages.
- **Pipeline**: The end-to-end system orchestrating input capture, extraction, scoring, review, persistence, and feedback.
- **Assembler**: The component responsible for stitching multiple scanned pages into a single logical BMR record.
- **Extraction_Model**: An interchangeable LLM (vision/multimodal) that parses handwritten content from assembled BMR inputs and outputs structured data.
- **Confidence_Scorer**: An LLM-as-judge component that assigns a confidence score (0.0–1.0) to each extracted field. May be the same model as the Extraction_Model or a separate model.
- **Review_UI**: The Streamlit-based web application where human reviewers inspect, edit, approve, or flag extraction results.
- **Record**: A structured data object (JSON / Pydantic) representing the extracted content of a single BMR, including fields, confidence scores, and audit metadata.
- **Reviewer**: A human operator who uses the Review_UI to validate extraction results.
- **Re_Extraction_Queue**: A queue of flagged records awaiting another extraction pass, each annotated with reviewer notes.
- **Feedback_Loop**: The component that feeds validated records back into the training/fine-tuning pipeline for the Extraction_Model and Confidence_Scorer.
- **Schema**: The structure of fields within a BMR. The Schema is inferred from the data by the Extraction_Model, not hardcoded.

## Requirements

### Requirement 1: Input Capture

**User Story:** As a pipeline operator, I want to ingest scanned BMR pages as images or PDFs, so that handwritten records can enter the digitization pipeline.

#### Acceptance Criteria

1. WHEN a scanned BMR page is provided as a PNG, JPEG, or TIFF image, THE Pipeline SHALL accept the page as valid input.
2. WHEN a scanned BMR page is provided as a PDF file, THE Pipeline SHALL accept the page as valid input.
3. IF an input file is not a supported format (PNG, JPEG, TIFF, or PDF), THEN THE Pipeline SHALL reject the file and return an error message specifying the unsupported format.
4. IF an input file is corrupted or unreadable, THEN THE Pipeline SHALL reject the file and return an error message indicating the file could not be read.

### Requirement 2: Multi-Page Assembly

**User Story:** As a pipeline operator, I want multiple scanned pages to be assembled into a single logical BMR record, so that extraction operates on complete records rather than individual pages.

#### Acceptance Criteria

1. WHEN multiple pages belonging to the same BMR are provided, THE Assembler SHALL stitch the pages into a single logical Record in the order specified.
2. WHEN a single-page BMR is provided, THE Assembler SHALL produce a Record containing that single page without modification.
3. THE Assembler SHALL preserve the original page images within the assembled Record for downstream reference.
4. IF no pages are provided for assembly, THEN THE Assembler SHALL return an error indicating that at least one page is required.

### Requirement 3: Extraction & Schema Learning

**User Story:** As a pipeline operator, I want an LLM to extract structured data from assembled BMR inputs and infer the schema from the data, so that the pipeline adapts to varying BMR formats without hardcoded field definitions.

#### Acceptance Criteria

1. WHEN an assembled Record is submitted for extraction, THE Extraction_Model SHALL parse the handwritten content and output structured data as JSON conforming to a Pydantic model.
2. THE Extraction_Model SHALL infer the Schema of the BMR from the input data rather than relying on hardcoded field definitions.
3. WHEN the Extraction_Model produces output, THE Pipeline SHALL include the extracted field names and values in the resulting Record.
4. THE Pipeline SHALL support swapping the Extraction_Model implementation without changes to the rest of the pipeline (provider-agnostic interface).
5. IF the Extraction_Model fails to extract any fields from the input, THEN THE Pipeline SHALL mark the Record as failed extraction and include the error details.

### Requirement 4: Confidence Scoring

**User Story:** As a reviewer, I want each extracted field to have a confidence score, so that I can prioritize my review effort on low-confidence fields.

#### Acceptance Criteria

1. WHEN extraction is complete for a Record, THE Confidence_Scorer SHALL assign a confidence score between 0.0 and 1.0 (inclusive) to each extracted field.
2. THE Pipeline SHALL support configuring the Confidence_Scorer to use the same model as the Extraction_Model or a separate model.
3. WHEN the Confidence_Scorer produces scores, THE Pipeline SHALL store each field-level score within the Record.
4. IF the Confidence_Scorer fails to score a field, THEN THE Pipeline SHALL assign a score of 0.0 to that field and flag the scoring failure in the Record metadata.

### Requirement 5: Human Review UI

**User Story:** As a reviewer, I want a Streamlit-based interface to view, edit, approve, and flag extraction results, so that I can validate BMR data efficiently.

#### Acceptance Criteria

1. THE Review_UI SHALL display each extracted field alongside its confidence score for a given Record.
2. THE Review_UI SHALL allow the Reviewer to edit or correct extracted field values inline.
3. WHEN the Reviewer approves an individual field, THE Review_UI SHALL mark that field as approved in the Record.
4. WHEN the Reviewer approves an entire Record, THE Review_UI SHALL mark all fields in the Record as approved.
5. WHEN the Reviewer flags a Record for re-extraction, THE Review_UI SHALL require the Reviewer to provide notes explaining the issue.
6. THE Review_UI SHALL display the original scanned page images alongside the extracted data for visual comparison.
7. THE Review_UI SHALL present Records ordered by extraction date, with the most recent Records first.

### Requirement 6: Re-Extraction

**User Story:** As a reviewer, I want flagged records to be sent back for another extraction pass with my notes as context, so that the model can produce improved results.

#### Acceptance Criteria

1. WHEN a Record is flagged for re-extraction, THE Pipeline SHALL place the Record in the Re_Extraction_Queue with the Reviewer notes attached.
2. WHEN a Record from the Re_Extraction_Queue is processed, THE Extraction_Model SHALL receive the Reviewer notes as additional context for the extraction.
3. WHEN re-extraction is complete, THE Pipeline SHALL replace the previous extraction results in the Record with the new results while preserving the extraction history.
4. THE Pipeline SHALL retain all previous extraction attempts and their confidence scores in the Record extraction history.

### Requirement 7: Persistence

**User Story:** As a pipeline operator, I want approved records to be saved locally as JSON files with full audit trails, so that validated data is durable and traceable.

#### Acceptance Criteria

1. WHEN a Record is fully approved, THE Pipeline SHALL save the Record as a JSON file to local storage.
2. THE Pipeline SHALL include the extraction history, confidence scores, and all Reviewer actions in the persisted JSON file.
3. THE Pipeline SHALL assign a unique identifier to each persisted Record.
4. IF the Pipeline fails to write a Record to local storage, THEN THE Pipeline SHALL report the write failure and retain the Record in memory for retry.

### Requirement 8: Active Feedback Loop

**User Story:** As a pipeline operator, I want validated records to automatically feed back into the model training pipeline, so that extraction and scoring accuracy improve over time.

#### Acceptance Criteria

1. WHEN a validated Record is persisted, THE Feedback_Loop SHALL automatically add the Record to the training dataset for the Extraction_Model.
2. WHEN a validated Record is persisted, THE Feedback_Loop SHALL automatically add the Record to the training dataset for the Confidence_Scorer.
3. THE Feedback_Loop SHALL trigger a retraining cycle when new validated Records are available.
4. THE Pipeline SHALL log each retraining trigger event, including the number of new Records added to the training dataset.

### Requirement 9: Record Serialization Round-Trip

**User Story:** As a pipeline operator, I want to ensure that records can be serialized to JSON and deserialized back without data loss, so that persistence is reliable.

#### Acceptance Criteria

1. THE Pipeline SHALL serialize Record objects to JSON using a defined schema.
2. THE Pipeline SHALL deserialize JSON files back into Record objects using the same schema.
3. FOR ALL valid Record objects, serializing to JSON then deserializing back SHALL produce an equivalent Record object (round-trip property).
4. IF a JSON file does not conform to the Record schema, THEN THE Pipeline SHALL return a descriptive error identifying the schema violation.
