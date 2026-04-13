"""Re-extraction queue for the BMR Digitization Pipeline.

Manages flagged records awaiting re-extraction, persisted as JSON files.
"""

import json
from pathlib import Path

from bmr_pipeline.config import QUEUE_DIR


class ReExtractionQueue:
    """Manages flagged records awaiting re-extraction with reviewer notes.

    Each queue item is persisted as a JSON file named ``{record_id}.json``
    in the queue directory.
    """

    def __init__(self, queue_dir: Path = QUEUE_DIR) -> None:
        self._queue_dir = queue_dir
        self._queue_dir.mkdir(parents=True, exist_ok=True)

    def enqueue(self, record_id: str, reviewer_notes: str) -> None:
        """Add a record to the re-extraction queue.

        Args:
            record_id: The unique identifier of the record to re-extract.
            reviewer_notes: Reviewer notes explaining the issue.
        """
        file_path = self._queue_dir / f"{record_id}.json"
        data = {"record_id": record_id, "reviewer_notes": reviewer_notes}
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def dequeue(self) -> tuple[str, str] | None:
        """Remove and return the oldest queue item.

        Returns:
            A tuple of ``(record_id, reviewer_notes)`` or ``None`` if the
            queue is empty.
        """
        items = sorted(self._queue_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        if not items:
            return None

        file_path = items[0]
        data = json.loads(file_path.read_text(encoding="utf-8"))
        file_path.unlink()
        return data["record_id"], data["reviewer_notes"]

    def pending(self) -> list[str]:
        """Return the record IDs of all items currently in the queue."""
        result: list[str] = []
        for file_path in self._queue_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                result.append(data["record_id"])
            except Exception:
                continue
        return result
