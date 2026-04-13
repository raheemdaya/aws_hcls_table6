"""Property-based tests for BMR pipeline data models."""

from datetime import datetime

from hypothesis import given, settings, strategies as st

from bmr_pipeline.models import (
    ExtractedField,
    ExtractionAttempt,
    FieldStatus,
    PageImage,
    Record,
    RecordStatus,
    ReviewerAction,
)


# --- Hypothesis Strategies ---

field_names = st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N", "P")))

extracted_field_strategy = st.builds(
    ExtractedField,
    name=field_names,
    value=st.one_of(st.none(), st.text(max_size=200)),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    status=st.sampled_from([FieldStatus.PENDING, FieldStatus.EDITED]),
)

record_with_fields_strategy = st.builds(
    Record,
    current_fields=st.lists(extracted_field_strategy, min_size=1, max_size=20),
)


# Feature: bmr-digitization-pipeline, Property 5: Record approval marks all fields approved
@settings(max_examples=100)
@given(record=record_with_fields_strategy)
def test_approve_all_fields_marks_every_field_approved(record: Record) -> None:
    """
    Property 5: Record approval marks all fields approved.

    For any Record with one or more extracted fields, approving the entire
    Record SHALL result in every field having status APPROVED.

    **Validates: Requirements 5.3, 5.4**
    """
    # Pre-condition: record has at least one field
    assert len(record.current_fields) >= 1

    # Act
    record.approve_all_fields()

    # Assert: every field is now APPROVED
    for field in record.current_fields:
        assert field.status == FieldStatus.APPROVED, (
            f"Field '{field.name}' has status {field.status}, expected APPROVED"
        )


# Feature: bmr-digitization-pipeline, Property 9: Unique record IDs
@settings(max_examples=100)
@given(num_records=st.integers(min_value=2, max_value=50))
def test_record_ids_are_unique(num_records: int) -> None:
    """
    Property 9: Unique record IDs.

    For any set of Records created by the pipeline, all Record IDs SHALL be
    distinct.

    **Validates: Requirements 7.3**
    """
    records = [Record() for _ in range(num_records)]
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids)), (
        f"Duplicate IDs found among {num_records} records: "
        f"{[rid for rid in ids if ids.count(rid) > 1]}"
    )


# --- Additional Hypothesis Strategies for Property 10 ---

datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2099, 12, 31),
)

page_image_strategy = st.builds(
    PageImage,
    page_number=st.integers(min_value=1, max_value=500),
    file_path=st.text(min_size=1, max_size=100, alphabet=st.characters(categories=("L", "N", "P"))),
    original_filename=st.text(min_size=1, max_size=100, alphabet=st.characters(categories=("L", "N", "P"))),
)

extraction_attempt_strategy = st.builds(
    ExtractionAttempt,
    attempt_number=st.integers(min_value=1, max_value=100),
    timestamp=datetime_strategy,
    fields=st.lists(extracted_field_strategy, min_size=0, max_size=10),
    reviewer_notes=st.one_of(st.none(), st.text(max_size=200)),
    model_id=st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N"))),
)

reviewer_action_strategy = st.builds(
    ReviewerAction,
    action=st.sampled_from(["approve_field", "approve_record", "edit_field", "flag_record"]),
    timestamp=datetime_strategy,
    field_name=st.one_of(st.none(), field_names),
    old_value=st.one_of(st.none(), st.text(max_size=200)),
    new_value=st.one_of(st.none(), st.text(max_size=200)),
    notes=st.one_of(st.none(), st.text(max_size=200)),
)

full_record_strategy = st.builds(
    Record,
    status=st.sampled_from(list(RecordStatus)),
    pages=st.lists(page_image_strategy, min_size=0, max_size=5),
    current_fields=st.lists(extracted_field_strategy, min_size=0, max_size=10),
    extraction_history=st.lists(extraction_attempt_strategy, min_size=0, max_size=5),
    reviewer_actions=st.lists(reviewer_action_strategy, min_size=0, max_size=5),
    created_at=datetime_strategy,
    updated_at=datetime_strategy,
    inferred_schema=st.one_of(st.none(), st.fixed_dictionaries({"type": st.just("object")})),
)


# Feature: bmr-digitization-pipeline, Property 10: Record serialization round-trip
@settings(max_examples=100)
@given(record=full_record_strategy)
def test_record_serialization_round_trip(record: Record) -> None:
    """
    Property 10: Record serialization round-trip.

    For any valid Record object (including fields, extraction history,
    reviewer actions, and confidence scores), serializing to JSON and then
    deserializing back SHALL produce an equivalent Record object.

    **Validates: Requirements 9.1, 9.2, 9.3**
    """
    # Serialize to JSON
    json_str = record.model_dump_json()

    # Deserialize back
    restored = Record.model_validate_json(json_str)

    # Assert round-trip equivalence
    assert restored == record, (
        f"Round-trip mismatch:\n"
        f"  Original ID: {record.id}\n"
        f"  Restored ID: {restored.id}\n"
        f"  Original status: {record.status}\n"
        f"  Restored status: {restored.status}\n"
        f"  Original fields count: {len(record.current_fields)}\n"
        f"  Restored fields count: {len(restored.current_fields)}\n"
        f"  Original history count: {len(record.extraction_history)}\n"
        f"  Restored history count: {len(restored.extraction_history)}"
    )
