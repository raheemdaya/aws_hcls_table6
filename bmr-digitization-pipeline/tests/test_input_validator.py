"""Property-based tests for InputValidator."""

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.models import InputValidationError, ValidatedInput


SUPPORTED_EXTENSIONS = ["png", "jpeg", "jpg", "tiff", "tif", "pdf"]


# Feature: bmr-digitization-pipeline, Property 1: Supported format acceptance
@settings(max_examples=100)
@given(
    ext=st.sampled_from(SUPPORTED_EXTENSIONS),
    content=st.binary(min_size=1, max_size=256),
)
def test_supported_format_acceptance(ext: str, content: bytes) -> None:
    """
    Property 1: Supported format acceptance.

    For any file with a supported extension (PNG, JPEG, JPG, TIFF, TIF, PDF)
    and valid content, the InputValidator SHALL accept the file as valid input
    without error.

    **Validates: Requirements 1.1, 1.2**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / f"test_file.{ext}"
        file_path.write_bytes(content)

        validator = InputValidator()
        result = validator.validate(file_path)

        assert isinstance(result, ValidatedInput)
        assert result.format == ext
        assert result.file_path == str(file_path)


# Feature: bmr-digitization-pipeline, Property 2: Unsupported format rejection
@settings(max_examples=100)
@given(
    ext=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=10,
    ).filter(lambda e: e.lower() not in {"png", "jpeg", "jpg", "tiff", "tif", "pdf"}),
    content=st.binary(min_size=1, max_size=256),
)
def test_unsupported_format_rejection(ext: str, content: bytes) -> None:
    """
    Property 2: Unsupported format rejection.

    For any file with an extension not in the supported set (PNG, JPEG, JPG,
    TIFF, TIF, PDF), the InputValidator SHALL reject the file and return an
    error message that contains the unsupported format name.

    **Validates: Requirements 1.3**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / f"test_file.{ext}"
        file_path.write_bytes(content)

        validator = InputValidator()
        try:
            validator.validate(file_path)
            assert False, f"Expected InputValidationError for extension '{ext}'"
        except InputValidationError as exc:
            # The error message must contain the unsupported format name
            assert ext.lower() in str(exc).lower(), (
                f"Error message '{exc}' does not contain the unsupported format '{ext}'"
            )


import pytest


# --- Unit Tests for InputValidator (Requirement 1.4) ---


def test_corrupted_unreadable_file_rejection() -> None:
    """Corrupted/unreadable files must be rejected with a descriptive error.

    **Validates: Requirements 1.4**
    """
    non_existent = Path("/tmp/does_not_exist_bmr_test_file.png")
    # Ensure it really doesn't exist
    if non_existent.exists():
        non_existent.unlink()

    validator = InputValidator()
    with pytest.raises(InputValidationError, match="could not be read"):
        validator.validate(non_existent)


@pytest.mark.parametrize("ext", ["png", "jpeg", "jpg", "tiff", "tif", "pdf"])
def test_each_supported_format_individually(ext: str) -> None:
    """Each supported format should be accepted when the file is valid.

    **Validates: Requirements 1.2**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / f"sample.{ext}"
        file_path.write_bytes(b"\x00valid content")

        validator = InputValidator()
        result = validator.validate(file_path)

        assert isinstance(result, ValidatedInput)
        assert result.format == ext
        assert result.file_size > 0
