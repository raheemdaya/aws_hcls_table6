"""Process test data: bmr/ directory files + first 10 handwritten PDFs."""

from pathlib import Path

from bmr_pipeline.orchestrator import PipelineOrchestrator
from bmr_pipeline.input_validator import InputValidator
from bmr_pipeline.assembler import PageAssembler
from bmr_pipeline.bedrock_extraction import BedrockExtractionModel
from bmr_pipeline.bedrock_scoring import BedrockConfidenceScorer
from bmr_pipeline.record_store import RecordStore
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.feedback import FeedbackLoop

BMR_DIR = Path(__file__).resolve().parent.parent / "bmr"
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

# Collect files
bmr_files = sorted(BMR_DIR.glob("*.pdf"))
handwritten_files = sorted(HANDWRITTEN_DIR.glob("*.pdf"))[:10]
all_files = bmr_files + handwritten_files

print(f"=== Processing {len(bmr_files)} bmr/ files + {len(handwritten_files)} handwritten files ===")
print()

success = 0
failed = 0

for pdf in all_files:
    source = "bmr" if pdf.parent == BMR_DIR else "handwritten"
    try:
        record = orch.process([pdf])
        fc = len(record.current_fields)
        avg = sum(f.confidence for f in record.current_fields) / fc if fc else 0
        print(f"  ✓ [{source:11s}] {pdf.name:45s}  fields={fc:2d}  avg_conf={avg:.2f}")
        for f in record.current_fields[:8]:
            val = (f.value or "null")[:55]
            print(f"      {f.name:30s} = {val:55s} [{f.confidence:.2f}]")
        if fc > 8:
            print(f"      ... and {fc - 8} more fields")
        print()
        success += 1
    except Exception as e:
        print(f"  ✗ [{source:11s}] {pdf.name:45s}  ERROR: {e}")
        failed += 1

print(f"Processed: {success} success, {failed} failed, {success + failed} total")
print()
summaries = orch._store.list_records()
print(f"Total records in store: {len(summaries)}")
for s in summaries:
    print(f"  {s.id[:12]}…  status={s.status.value:15s}  fields={s.field_count}  avg_conf={s.avg_confidence:.2f}")
