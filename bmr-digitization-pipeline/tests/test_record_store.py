"""Property-based tests for RecordStore."""

from datetime import datetime, timedelta

from hypothesis import given, settings, strategies as st

from bmr_pipeline.models import Record
from bmr_pipeline.record_store import RecordStore


# Strategy: list of distinct datetime values for created_at timestamps
distinct_datetimes = st.lists(
    st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2099, 12, 31),
    ),
    min_size=2,
    max_size=15,
    unique=True,
)


# Feature: bmr-digitization-pipeline, Property 6: Records listed in descending date order
@settings(max_examples=100)
@given(timestamps=distinct_datetimes)
def test_list_records_returns_descending_date_order(
    timestamps: list[datetime], tmp_path_factory
) -> None:
    """
    Property 6: Records listed in descending date order.

    For any set of Records with distinct creation timestamps, listing Records
    SHALL return them ordered by creation date descending (most recent first).

    **Validates: Requirements 5.7**
    """
    storage_dir = tmp_path_factory.mktemp("records")
    store = RecordStore(storage_dir=storage_dir)

    # Create and save records with the generated timestamps
    for ts in timestamps:
        record = Record(created_at=ts, updated_at=ts)
        store.save(record)

    # List records
    summaries = store.list_records()

    # All saved records should be listed
    assert len(summaries) == len(timestamps)

    # Assert descending order by created_at
    for i in range(len(summaries) - 1):
        assert summaries[i].created_at >= summaries[i + 1].created_at, (
            f"Records not in descending date order at index {i}: "
            f"{summaries[i].created_at} should be >= {summaries[i + 1].created_at}"
        )


# --- Unit Tests for RecordStore (Task 8.3) ---

import pytest

from bmr_pipeline.models import PersistenceError, SchemaValidationError


def test_write_failure_raises_persistence_error(tmp_path):
    """Write failure raises PersistenceError and the record object remains intact.

    **Validates: Requirements 7.4**
    """
    # Point the store at a read-only directory to force a write failure
    read_only_dir = tmp_path / "readonly_records"
    read_only_dir.mkdir()

    store = RecordStore(storage_dir=read_only_dir)
    record = Record()

    # Make the directory read-only so file writes fail
    read_only_dir.chmod(0o444)

    try:
        with pytest.raises(PersistenceError):
            store.save(record)

        # Record object should still be intact in memory after the failure
        assert record.id is not None
        assert record.status is not None
        assert record.created_at is not None
    finally:
        # Restore permissions so tmp_path cleanup can proceed
        read_only_dir.chmod(0o755)


def test_invalid_json_deserialization_error(tmp_path):
    """Loading invalid JSON raises SchemaValidationError with a descriptive message.

    **Validates: Requirements 9.4**
    """
    store = RecordStore(storage_dir=tmp_path)

    # Write invalid JSON content to a record file
    bad_file = tmp_path / "bad-record.json"
    bad_file.write_text("{this is not valid json!!}", encoding="utf-8")

    with pytest.raises(SchemaValidationError, match="Invalid JSON for record bad-record"):
        store.load("bad-record")
