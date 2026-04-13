"""Tests for the ReExtractionQueue."""

import pytest
from pathlib import Path

from bmr_pipeline.queue import ReExtractionQueue


@pytest.fixture
def queue(tmp_path: Path) -> ReExtractionQueue:
    return ReExtractionQueue(queue_dir=tmp_path / "queue")


class TestReExtractionQueue:
    def test_enqueue_creates_json_file(self, queue: ReExtractionQueue) -> None:
        queue.enqueue("rec-1", "Missing field X")
        files = list(queue._queue_dir.glob("*.json"))
        assert len(files) == 1
        assert files[0].name == "rec-1.json"

    def test_dequeue_returns_enqueued_item(self, queue: ReExtractionQueue) -> None:
        queue.enqueue("rec-1", "Please re-check")
        result = queue.dequeue()
        assert result == ("rec-1", "Please re-check")

    def test_dequeue_removes_file(self, queue: ReExtractionQueue) -> None:
        queue.enqueue("rec-1", "notes")
        queue.dequeue()
        assert list(queue._queue_dir.glob("*.json")) == []

    def test_dequeue_empty_returns_none(self, queue: ReExtractionQueue) -> None:
        assert queue.dequeue() is None

    def test_pending_returns_all_record_ids(self, queue: ReExtractionQueue) -> None:
        queue.enqueue("a", "note-a")
        queue.enqueue("b", "note-b")
        assert sorted(queue.pending()) == ["a", "b"]

    def test_pending_empty_queue(self, queue: ReExtractionQueue) -> None:
        assert queue.pending() == []

    def test_dequeue_oldest_first(self, queue: ReExtractionQueue, tmp_path: Path) -> None:
        """Dequeue should return the oldest item based on file mtime."""
        import time
        queue.enqueue("first", "notes-1")
        time.sleep(0.05)
        queue.enqueue("second", "notes-2")
        result = queue.dequeue()
        assert result is not None
        assert result[0] == "first"

    def test_enqueue_overwrites_existing(self, queue: ReExtractionQueue) -> None:
        """Re-enqueuing the same record_id updates the notes."""
        queue.enqueue("rec-1", "old notes")
        queue.enqueue("rec-1", "new notes")
        result = queue.dequeue()
        assert result == ("rec-1", "new notes")


# Feature: bmr-digitization-pipeline, Property 7: Queue enqueue/dequeue preserves record ID and notes
from hypothesis import given, settings
from hypothesis import strategies as st


# Strategy: record_id used as filename, so restrict to alphanumeric + hyphens, min_size=1
_record_id_alphabet = st.characters(whitelist_categories=(), whitelist_characters="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
_record_id_strategy = st.text(alphabet=_record_id_alphabet, min_size=1, max_size=50)
_reviewer_notes_strategy = st.text(min_size=0, max_size=200)


@settings(max_examples=100)
@given(record_id=_record_id_strategy, reviewer_notes=_reviewer_notes_strategy)
def test_enqueue_dequeue_preserves_record_id_and_notes(record_id: str, reviewer_notes: str, tmp_path_factory) -> None:
    """Property 7: For any record ID and reviewer notes, enqueuing then dequeuing
    from the ReExtractionQueue SHALL return the same record ID and the same reviewer notes.

    **Validates: Requirements 6.1**
    """
    tmp_dir = tmp_path_factory.mktemp("queue")
    queue = ReExtractionQueue(queue_dir=tmp_dir)

    queue.enqueue(record_id, reviewer_notes)
    result = queue.dequeue()

    assert result is not None, "dequeue() returned None after enqueue"
    dequeued_id, dequeued_notes = result
    assert dequeued_id == record_id, f"record_id mismatch: expected {record_id!r}, got {dequeued_id!r}"
    assert dequeued_notes == reviewer_notes, f"reviewer_notes mismatch: expected {reviewer_notes!r}, got {dequeued_notes!r}"
