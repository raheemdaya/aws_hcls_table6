"""Property-based tests for BMR pipeline PageAssembler."""

from pathlib import Path

from hypothesis import given, settings, strategies as st

from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.models import ValidatedInput


# --- Hypothesis Strategies ---

SUPPORTED_FORMATS = ["png", "jpeg", "jpg", "tiff", "tif", "pdf"]

file_path_strategy = st.text(
    min_size=1, max_size=80, alphabet=st.characters(categories=("L", "N", "P"))
).map(lambda name: f"/scans/{name}.png")

validated_input_strategy = st.builds(
    ValidatedInput,
    file_path=file_path_strategy,
    format=st.sampled_from(SUPPORTED_FORMATS),
    file_size=st.integers(min_value=1, max_value=100_000_000),
)

pages_strategy = st.lists(validated_input_strategy, min_size=1, max_size=10)


# Feature: bmr-digitization-pipeline, Property 3: Assembly preserves page order and content
@settings(max_examples=100)
@given(pages=pages_strategy)
def test_assembly_preserves_page_order_and_content(pages: list[ValidatedInput]) -> None:
    """
    Property 3: Assembly preserves page order and content.

    For any non-empty list of validated pages, the PageAssembler SHALL produce
    a Record containing exactly the same pages in the same order, with all
    original page image references preserved.

    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    assembler = PageAssembler()
    record = assembler.assemble(pages)

    # Same number of pages
    assert len(record.pages) == len(pages), (
        f"Expected {len(pages)} pages in record, got {len(record.pages)}"
    )

    # Each page's file_path matches the corresponding input
    for idx, (page_image, validated) in enumerate(zip(record.pages, pages)):
        assert page_image.file_path == validated.file_path, (
            f"Page {idx}: file_path mismatch — "
            f"expected {validated.file_path!r}, got {page_image.file_path!r}"
        )

    # Page numbers are sequential starting from 1
    expected_numbers = list(range(1, len(pages) + 1))
    actual_numbers = [p.page_number for p in record.pages]
    assert actual_numbers == expected_numbers, (
        f"Page numbers not sequential: expected {expected_numbers}, got {actual_numbers}"
    )

    # Original filenames are preserved (derived from file_path)
    for idx, (page_image, validated) in enumerate(zip(record.pages, pages)):
        expected_filename = Path(validated.file_path).name
        assert page_image.original_filename == expected_filename, (
            f"Page {idx}: original_filename mismatch — "
            f"expected {expected_filename!r}, got {page_image.original_filename!r}"
        )


# --- Unit Tests for PageAssembler ---

import pytest

from bmr_pipeline.models import AssemblyError


def test_single_page_assembly() -> None:
    """A single-page BMR produces a Record with exactly one page, unmodified.

    **Validates: Requirements 2.2**
    """
    assembler = PageAssembler()
    page = ValidatedInput(file_path="/scans/page1.png", format="png", file_size=1024)

    record = assembler.assemble([page])

    assert len(record.pages) == 1
    assert record.pages[0].page_number == 1
    assert record.pages[0].file_path == "/scans/page1.png"
    assert record.pages[0].original_filename == "page1.png"


def test_empty_page_list_raises_assembly_error() -> None:
    """Assembling an empty page list raises AssemblyError.

    **Validates: Requirements 2.4**
    """
    assembler = PageAssembler()

    with pytest.raises(AssemblyError):
        assembler.assemble([])
