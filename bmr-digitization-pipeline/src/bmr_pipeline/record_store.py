"""JSON-based record persistence for the BMR Digitization Pipeline."""

from pathlib import Path

from bmr_pipeline.config import RECORDS_DIR
from bmr_pipeline.models import (
    PersistenceError,
    Record,
    RecordSummary,
    SchemaValidationError,
)


class RecordStore:
    """Persists Record objects as JSON files on disk."""

    def __init__(self, storage_dir: Path = RECORDS_DIR) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: Record) -> Path:
        """Serialize *record* to JSON and write to ``storage_dir/{record.id}.json``.

        Returns the path of the written file.
        Raises ``PersistenceError`` if the write fails.
        """
        file_path = self._storage_dir / f"{record.id}.json"
        try:
            json_data = record.model_dump_json(indent=2)
            file_path.write_text(json_data, encoding="utf-8")
        except Exception as exc:
            raise PersistenceError(
                f"Failed to write record {record.id} to {file_path}: {exc}"
            ) from exc
        return file_path

    def load(self, record_id: str) -> Record:
        """Read a JSON file and deserialize it into a ``Record``.

        Raises ``SchemaValidationError`` if the JSON cannot be deserialized
        into a valid ``Record``.
        """
        file_path = self._storage_dir / f"{record_id}.json"
        try:
            json_data = file_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SchemaValidationError(
                f"Record file not found: {file_path}"
            ) from exc
        except Exception as exc:
            raise SchemaValidationError(
                f"Failed to read record file {file_path}: {exc}"
            ) from exc

        try:
            return Record.model_validate_json(json_data)
        except Exception as exc:
            raise SchemaValidationError(
                f"Invalid JSON for record {record_id}: {exc}"
            ) from exc

    def list_records(self) -> list[RecordSummary]:
        """Return a summary of every persisted record, ordered by creation date descending."""
        summaries: list[RecordSummary] = []
        for file_path in self._storage_dir.glob("*.json"):
            try:
                json_data = file_path.read_text(encoding="utf-8")
                record = Record.model_validate_json(json_data)
            except Exception:
                # Skip files that cannot be parsed.
                continue

            field_count = len(record.current_fields)
            avg_confidence = (
                sum(f.confidence for f in record.current_fields) / field_count
                if field_count
                else 0.0
            )
            summaries.append(
                RecordSummary(
                    id=record.id,
                    status=record.status,
                    field_count=field_count,
                    avg_confidence=avg_confidence,
                    created_at=record.created_at,
                )
            )

        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries
