"""Feedback loop and retrain trigger for the BMR Digitization Pipeline."""

import json
import logging
from datetime import datetime
from pathlib import Path

from bmr_pipeline.config import RETRAIN_THRESHOLD, TRAINING_DIR
from bmr_pipeline.models import Record, RetrainEvent

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """Manages the training dataset and triggers retraining when new validated records are available."""

    def __init__(
        self,
        training_dir: Path = TRAINING_DIR,
        retrain_threshold: int = RETRAIN_THRESHOLD,
    ) -> None:
        self.training_dir = training_dir
        self.retrain_threshold = retrain_threshold
        self._new_records: int = 0
        self.training_dir.mkdir(parents=True, exist_ok=True)

    def add_validated_record(self, record: Record) -> None:
        """Serialize a validated record to JSON and save it to the training directory.

        Increments the new-records counter used by should_retrain().
        """
        dest = self.training_dir / f"{record.id}.json"
        dest.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        self._new_records += 1

    def should_retrain(self) -> bool:
        """Return True if the number of new records since last retrain meets or exceeds the threshold."""
        return self._new_records >= self.retrain_threshold

    def trigger_retrain(self) -> RetrainEvent:
        """Create a RetrainEvent, log it, and reset the new-records counter."""
        total = len(
            [f for f in self.training_dir.iterdir() if f.suffix == ".json"]
        )
        event = RetrainEvent(
            timestamp=datetime.utcnow(),
            records_added=self._new_records,
            total_training_records=total,
        )
        logger.info(
            "Retrain triggered: %d new records added, %d total training records",
            event.records_added,
            event.total_training_records,
        )
        self._new_records = 0
        return event
