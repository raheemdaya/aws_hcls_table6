"""Property-based tests for BMR pipeline confidence scoring."""

from hypothesis import given, settings, strategies as st

from bmr_pipeline.models import (
    ExtractedField,
    ExtractionResult,
    FieldScore,
    FieldStatus,
    PageImage,
    Record,
)
from bmr_pipeline.scoring import MockConfidenceScorer


# --- Hypothesis Strategies ---

field_names = st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N", "P")))

extracted_field_strategy = st.builds(
    ExtractedField,
    name=field_names,
    value=st.one_of(st.none(), st.text(max_size=200)),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    status=st.sampled_from(list(FieldStatus)),
)

page_image_strategy = st.builds(
    PageImage,
    page_number=st.integers(min_value=1, max_value=500),
    file_path=st.text(min_size=1, max_size=100, alphabet=st.characters(categories=("L", "N", "P"))),
    original_filename=st.text(min_size=1, max_size=100, alphabet=st.characters(categories=("L", "N", "P"))),
)

record_strategy = st.builds(
    Record,
    pages=st.lists(page_image_strategy, min_size=0, max_size=5),
)

extraction_result_strategy = st.builds(
    ExtractionResult,
    fields=st.lists(extracted_field_strategy, min_size=1, max_size=20),
    inferred_schema=st.just({"type": "object"}),
    model_id=st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N"))),
    error=st.none(),
)


# Feature: bmr-digitization-pipeline, Property 4: Confidence scores are in valid range
@settings(max_examples=100)
@given(record=record_strategy, extraction_result=extraction_result_strategy)
def test_confidence_scores_in_valid_range(record: Record, extraction_result: ExtractionResult) -> None:
    """
    Property 4: Confidence scores are in valid range.

    For any set of extracted fields submitted to the ConfidenceScorer, every
    returned field score SHALL be a float in the range [0.0, 1.0] inclusive,
    and every extracted field SHALL have a corresponding score.

    **Validates: Requirements 4.1, 4.3**
    """
    scorer = MockConfidenceScorer()
    scores = scorer.score(record, extraction_result)

    # Every extracted field must have a corresponding score
    extracted_field_names = {f.name for f in extraction_result.fields}
    scored_field_names = {s.field_name for s in scores}
    assert extracted_field_names == scored_field_names, (
        f"Mismatch between extracted fields and scored fields.\n"
        f"  Extracted: {extracted_field_names}\n"
        f"  Scored: {scored_field_names}\n"
        f"  Missing scores: {extracted_field_names - scored_field_names}\n"
        f"  Extra scores: {scored_field_names - extracted_field_names}"
    )

    # Every score must be in [0.0, 1.0]
    for field_score in scores:
        assert isinstance(field_score.confidence, float), (
            f"Score for '{field_score.field_name}' is not a float: {type(field_score.confidence)}"
        )
        assert 0.0 <= field_score.confidence <= 1.0, (
            f"Score for '{field_score.field_name}' is out of range: {field_score.confidence}"
        )


# --- Unit Tests ---

import pytest
from unittest.mock import patch

from bmr_pipeline.scoring import ConfidenceScorer, MockConfidenceScorer


def _make_record_and_extraction(field_names: list[str]) -> tuple[Record, ExtractionResult]:
    """Helper to build a Record and ExtractionResult with the given field names."""
    record = Record(pages=[])
    fields = [
        ExtractedField(name=name, value=f"val_{name}", confidence=0.5, status=FieldStatus.PENDING)
        for name in field_names
    ]
    extraction = ExtractionResult(
        fields=fields,
        inferred_schema={"type": "object"},
        model_id="test-model",
        error=None,
    )
    return record, extraction


class AlternativeConfidenceScorer:
    """A separate-model scorer implementation that satisfies the ConfidenceScorer protocol."""

    def score(self, record: Record, extraction_result: ExtractionResult) -> list[FieldScore]:
        # Always returns a fixed confidence of 0.75 for every field
        return [
            FieldScore(field_name=f.name, confidence=0.75)
            for f in extraction_result.fields
        ]


def test_scorer_configuration_same_vs_separate() -> None:
    """Demonstrate that the ConfidenceScorer protocol can be satisfied by different
    implementations (same model scorer vs separate model scorer), verifying the
    configurable nature.

    **Validates: Requirements 4.2**
    """
    # Both implementations satisfy the runtime-checkable protocol
    same_model_scorer = MockConfidenceScorer()
    separate_model_scorer = AlternativeConfidenceScorer()

    assert isinstance(same_model_scorer, ConfidenceScorer), (
        "MockConfidenceScorer should satisfy the ConfidenceScorer protocol"
    )
    assert isinstance(separate_model_scorer, ConfidenceScorer), (
        "AlternativeConfidenceScorer should satisfy the ConfidenceScorer protocol"
    )

    # Both produce valid scores for the same input
    record, extraction = _make_record_and_extraction(["batch_id", "product_name"])

    scores_same = same_model_scorer.score(record, extraction)
    scores_separate = separate_model_scorer.score(record, extraction)

    # Both return one score per field
    assert len(scores_same) == 2
    assert len(scores_separate) == 2

    # Both return scores in valid range
    for s in scores_same + scores_separate:
        assert 0.0 <= s.confidence <= 1.0

    # The separate scorer returns its fixed 0.75 value
    for s in scores_separate:
        assert s.confidence == 0.75

    # A function accepting the protocol type works with either implementation
    def run_scoring(scorer: ConfidenceScorer) -> list[FieldScore]:
        return scorer.score(record, extraction)

    assert len(run_scoring(same_model_scorer)) == 2
    assert len(run_scoring(separate_model_scorer)) == 2


def test_scoring_failure_defaults_to_zero() -> None:
    """When scoring fails for a field (e.g., the hash function raises an exception),
    the score for that field defaults to 0.0.

    **Validates: Requirements 4.4**
    """
    scorer = MockConfidenceScorer()
    record, extraction = _make_record_and_extraction(["good_field", "bad_field"])

    # Patch _hash_score to raise on the "bad_field"
    original_hash_score = MockConfidenceScorer._hash_score

    def failing_hash_score(record_id: str, field_name: str) -> float:
        if field_name == "bad_field":
            raise ValueError("Simulated hash failure")
        return original_hash_score(record_id, field_name)

    with patch.object(MockConfidenceScorer, "_hash_score", staticmethod(failing_hash_score)):
        scores = scorer.score(record, extraction)

    score_map = {s.field_name: s.confidence for s in scores}

    # The good field should have a normal score in [0.0, 1.0]
    assert 0.0 <= score_map["good_field"] <= 1.0

    # The bad field should default to 0.0 due to the scoring failure
    assert score_map["bad_field"] == 0.0, (
        f"Expected 0.0 for failed scoring, got {score_map['bad_field']}"
    )

    # All fields still get a score (no field is dropped)
    assert len(scores) == 2
