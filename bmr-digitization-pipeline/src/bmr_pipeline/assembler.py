"""Multi-page assembly for the BMR Digitization Pipeline."""

import uuid
from pathlib import Path

from bmr_pipeline.models import AssemblyError, PageImage, Record, ValidatedInput


class PageAssembler:
    """Stitches multiple validated pages into a single logical Record."""

    def assemble(
        self, pages: list[ValidatedInput], record_id: str | None = None
    ) -> Record:
        """Assemble validated pages into a single Record.

        Args:
            pages: List of validated input pages to assemble.
            record_id: Optional identifier for the record. A UUID is generated
                if not provided.

        Returns:
            A Record containing PageImage entries for each input page,
            preserving the original order.

        Raises:
            AssemblyError: If the pages list is empty.
        """
        if not pages:
            raise AssemblyError("At least one page is required")

        if record_id is None:
            record_id = str(uuid.uuid4())

        page_images = [
            PageImage(
                page_number=idx + 1,
                file_path=page.file_path,
                original_filename=Path(page.file_path).name,
            )
            for idx, page in enumerate(pages)
        ]

        return Record(id=record_id, pages=page_images)
