"""ConfidenceScorer protocol and mock implementation for the BMR Digitization Pipeline."""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from bmr_pipeline.models import (
    ExtractionResult,
    FieldScore,
    Record,
    ScoringError,
)


@runtime_checkable
class ConfidenceScorer(Protocol):
    """Provider-agnostic interface for confidence scoring.

    Scores each extracted field on a 0.0–1.0 scale. Configurable to use
    the same model as the ExtractionModel or a separate one.
    """

    def score(self, record: Record, extraction_result: ExtractionResult) -> list[FieldScore]:
        """Score each extracted field for confidence.

        Args:
            record: The assembled record with page images.
            extraction_result: The extraction output to score.

        Returns:
            A list of FieldScore objects, one per extracted field.
            Returns 0.0 for fields that fail scoring.
        """
        ...


class MockConfidenceScorer:
    """Mock implementation of ConfidenceScorer for testing.

    Generates deterministic confidence scores using a hash of the field name
    and record ID, ensuring reproducible results across test runs.
    """

    def score(self, record: Record, extraction_result: ExtractionResult) -> list[FieldScore]:
        """Return deterministic confidence scores for each extracted field.

        Scores are derived from a hash of the record ID and field name,
        producing values in [0.0, 1.0]. If scoring fails for an individual
        field, that field receives a score of 0.0.

        Args:
            record: The assembled record with page images.
            extraction_result: The extraction output to score.

        Returns:
            A list of FieldScore objects, one per extracted field.
        """
        scores: list[FieldScore] = []
        for field in extraction_result.fields:
            try:
                confidence = self._hash_score(record.id, field.name)
                scores.append(FieldScore(field_name=field.name, confidence=confidence))
            except Exception:
                # Scoring failure: assign 0.0 per requirement 4.4
                scores.append(FieldScore(field_name=field.name, confidence=0.0))
        return scores

    @staticmethod
    def _hash_score(record_id: str, field_name: str) -> float:
        """Produce a deterministic score in [0.0, 1.0] from record ID and field name."""
        digest = hashlib.sha256(f"{record_id}:{field_name}".encode()).hexdigest()
        # Use first 8 hex chars → integer in [0, 2^32), then normalise
        return int(digest[:8], 16) / 0xFFFFFFFF
