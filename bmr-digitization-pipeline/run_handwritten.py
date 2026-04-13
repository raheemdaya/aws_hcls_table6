"""Process handwritten BMR PDFs from the handwritten/ directory."""

import sys
from pathlib import Path

# The handwritten dir is at the workspace root, one level up from this project
HANDWRITTEN_DIR = Path(__file__).resolve().parent.parent / "handwritten"

from bmr_pipeline.orchestrator import PipelineOrchestrator
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.extraction import MockExtractionModel
from bmr_pipeline.scoring import MockConfidenceScorer
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.feedback import FeedbackLoop

orch = PipelineOrchestrator(
    validator=InputValidator(),
    assembler=PageAssembler(),
    extractor=MockExtractionModel(),
    scorer=MockConfidenceScorer(),
    store=RecordStore(),
    queue=ReExtractionQueue(),
    feedback=FeedbackLoop(),
)

pdfs = sorted(HANDWRITTEN_DIR.glob("*.pdf"))
print(f"Found {len(pdfs)} handwritten BMR PDFs in {HANDWRITTEN_DIR}")
print()

success = 0
failed = 0

for pdf in pdfs:
    try:
        record = orch.process([pdf])
        tag = pdf.stem.split("-")[-1]  # clean, messy, or partial
        avg_conf = sum(f.confidence for f in record.current_fields) / len(record.current_fields) if record.current_fields else 0
        print(f"  ✓ {pdf.name:45s}  id={record.id[:8]}…  fields={len(record.current_fields)}  avg_conf={avg_conf:.3f}  [{tag}]")
        success += 1
    except Exception as e:
        print(f"  ✗ {pdf.name:45s}  ERROR: {e}")
        failed += 1

print()
print(f"Processed: {success} success, {failed} failed, {success + failed} total")
print()

# Show summary from the store
summaries = orch._store.list_records()
print(f"Total records in store: {len(summaries)}")
print(f"  Pending review: {sum(1 for s in summaries if s.status.value == 'pending_review')}")
print(f"  Approved:       {sum(1 for s in summaries if s.status.value == 'approved')}")
print(f"  Failed:         {sum(1 for s in summaries if s.status.value == 'failed')}")
