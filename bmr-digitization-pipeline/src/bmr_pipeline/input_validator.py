"""Input file validation for the BMR Digitization Pipeline."""

from pathlib import Path

from bmr_pipeline.config import SUPPORTED_FORMATS
from bmr_pipeline.models import InputValidationError, ValidatedInput


class InputValidator:
    """Validates incoming files against supported formats and readability."""

    SUPPORTED_FORMATS: set[str] = SUPPORTED_FORMATS

    def validate(self, file_path: Path) -> ValidatedInput:
        """Validate file format and readability.

        Args:
            file_path: Path to the file to validate.

        Returns:
            ValidatedInput with file metadata on success.

        Raises:
            InputValidationError: If the file format is unsupported or the file
                is corrupted/unreadable.
        """
        extension = file_path.suffix.lstrip(".").lower()

        if extension not in self.SUPPORTED_FORMATS:
            raise InputValidationError(
                f"Unsupported format: {extension or '(no extension)'}"
            )

        try:
            file_size = file_path.stat().st_size
            with open(file_path, "rb") as f:
                f.read(1)
        except (OSError, IOError) as exc:
            raise InputValidationError(
                f"File could not be read: {file_path}"
            ) from exc

        return ValidatedInput(
            file_path=str(file_path),
            format=extension,
            file_size=file_size,
        )
