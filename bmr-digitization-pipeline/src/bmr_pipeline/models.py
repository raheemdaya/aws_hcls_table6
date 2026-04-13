"""Pydantic data models and custom exceptions for the BMR Digitization Pipeline."""

from datetime import datetime
from enum import Enum

import uuid
from pydantic import BaseModel, Field


# --- Custom Exception Hierarchy ---


class PipelineError(Exception):
    """Base exception for all pipeline errors."""


class InputValidationError(PipelineError):
    """Raised when input file validation fails."""


class AssemblyError(PipelineError):
    """Raised when page assembly fails."""


class ExtractionError(PipelineError):
    """Raised when data extraction fails."""


class ScoringError(PipelineError):
    """Raised when confidence scoring fails."""


class PersistenceError(PipelineError):
    """Raised when record persistence (write/read) fails."""


class SchemaValidationError(PipelineError):
    """Raised when JSON deserialization fails due to schema violations."""


# --- Enums ---


class FieldStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"


class RecordStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FLAGGED = "flagged"
    FAILED = "failed"


# --- Data Models ---


class ExtractedField(BaseModel):
    name: str
    value: str | None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    status: FieldStatus = FieldStatus.PENDING
    original_value: str | None = None  # Preserved when edited


class ExtractionAttempt(BaseModel):
    attempt_number: int
    timestamp: datetime
    fields: list[ExtractedField]
    reviewer_notes: str | None = None  # Notes that guided this attempt
    model_id: str  # Which model performed extraction


class ReviewerAction(BaseModel):
    action: str  # "approve_field", "approve_record", "edit_field", "flag_record"
    timestamp: datetime
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    notes: str | None = None


class PageImage(BaseModel):
    page_number: int
    file_path: str
    original_filename: str


class Record(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: RecordStatus = RecordStatus.PENDING_REVIEW
    pages: list[PageImage] = []
    current_fields: list[ExtractedField] = []
    extraction_history: list[ExtractionAttempt] = []
    reviewer_actions: list[ReviewerAction] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    inferred_schema: dict | None = None  # Schema learned from extraction

    def approve_all_fields(self) -> None:
        """Set every field's status to APPROVED."""
        for field in self.current_fields:
            field.status = FieldStatus.APPROVED


class ExtractionResult(BaseModel):
    fields: list[ExtractedField]
    inferred_schema: dict
    model_id: str
    error: str | None = None


class FieldScore(BaseModel):
    field_name: str
    confidence: float = Field(ge=0.0, le=1.0)


class RetrainEvent(BaseModel):
    timestamp: datetime
    records_added: int
    total_training_records: int


class RecordSummary(BaseModel):
    id: str
    status: RecordStatus
    field_count: int
    avg_confidence: float
    created_at: datetime


class ValidatedInput(BaseModel):
    file_path: str
    format: str
    file_size: int
