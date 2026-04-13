"""Unit tests for FeedbackLoop.

Tests retraining trigger logic and logging behaviour.
**Validates: Requirements 8.3, 8.4**
"""

import logging

import pytest

from bmr_pipeline.feedback import FeedbackLoop
from bmr_pipeline.models import Record, RetrainEvent


def _make_loop(tmp_path, threshold=2):
    """Create a FeedbackLoop with a low threshold pointing at a temp directory."""
    return FeedbackLoop(training_dir=tmp_path / "training", retrain_threshold=threshold)


def test_retrain_trigger_fires_when_threshold_met(tmp_path):
    """Adding records up to the threshold makes should_retrain() True and
    trigger_retrain() returns a valid RetrainEvent.

    **Validates: Requirements 8.3**
    """
    loop = _make_loop(tmp_path, threshold=2)

    loop.add_validated_record(Record())
    assert not loop.should_retrain()

    loop.add_validated_record(Record())
    assert loop.should_retrain()

    event = loop.trigger_retrain()

    assert isinstance(event, RetrainEvent)
    assert event.records_added == 2
    assert event.total_training_records == 2
    assert event.timestamp is not None


def test_retrain_trigger_logging(tmp_path, caplog):
    """trigger_retrain() logs the number of new and total training records.

    **Validates: Requirements 8.4**
    """
    loop = _make_loop(tmp_path, threshold=1)
    loop.add_validated_record(Record())

    with caplog.at_level(logging.INFO, logger="bmr_pipeline.feedback"):
        loop.trigger_retrain()

    assert len(caplog.records) == 1
    msg = caplog.records[0].message
    assert "1 new records added" in msg
    assert "1 total training records" in msg


def test_should_retrain_false_below_threshold(tmp_path):
    """Adding fewer records than the threshold keeps should_retrain() False.

    **Validates: Requirements 8.3**
    """
    loop = _make_loop(tmp_path, threshold=5)

    for _ in range(4):
        loop.add_validated_record(Record())

    assert not loop.should_retrain()


def test_trigger_retrain_resets_counter(tmp_path):
    """After triggering retrain the counter resets and should_retrain() is False.

    **Validates: Requirements 8.3**
    """
    loop = _make_loop(tmp_path, threshold=2)

    loop.add_validated_record(Record())
    loop.add_validated_record(Record())
    assert loop.should_retrain()

    loop.trigger_retrain()

    assert not loop.should_retrain()
