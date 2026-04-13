"""Process handwritten BMR PDFs using real Bedrock Claude extraction."""

import sys
from pathlib import Path

from bmr_pipeline.orchestrator import PipelineOrchestrator
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.bedrock_extraction import BedrockExtractionModel
from bmr_pipeline.bedrock_scoring import BedrockConfidenceScorer
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.feedback import FeedbackLoop

HANDWRITTEN_DIR = Path(__file__).resolve().parent.parent / "handwritten"

orch = PipelineOrchestrator(
    validator=InputValidator(),
    assembler=PageAssembler(),
    extractor=BedrockExtractionModel(),
    scorer=BedrockConfidenceScorer(),
    store=RecordStore(),
    queue=ReExtractionQueue(),
    feedback=FeedbackLoop(),
)

pdfs = sorted(HANDWRITTEN_DIR.glob("*.pdf"))
# Process a subset by default (pass --all to process everything)
if "--all" not in sys.argv:
    pdfs = pdfs[:5]
    print(f"Processing first 5 of {len(list(HANDWRITTEN_DIR.glob('*.pdf')))} PDFs (use --all for all)")
else:
    print(f"Processing all {len(pdfs)} PDFs")
print()

success = 0
failed = 0

for pdf in pdfs:
    try:
        record = orch.process([pdf])
        field_count = len(record.current_fields)
        avg_conf = (
            sum(f.confidence for f in record.current_fields) / field_count
            if field_count else 0
        )
        print(f"  ✓ {pdf.name:45s}  fields={field_count:2d}  avg_conf={avg_conf:.2f}")
        for f in record.current_fields:
            val = (f.value or "null")[:50]
            print(f"      {f.name:30s} = {val:50s}  [{f.confidence:.2f}]")
        print()
        success += 1
    except Exception as e:
        print(f"  ✗ {pdf.name:45s}  ERROR: {e}")
        failed += 1

print(f"\nProcessed: {success} success, {failed} failed")
summaries = orch._store.list_records()
print(f"Total records in store: {len(summaries)}")
