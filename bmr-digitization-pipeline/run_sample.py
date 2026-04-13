"""Process sample BMR data through the pipeline."""

from pathlib import Path
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

sample_dir = Path("data/sample_bmr")
pages = sorted(sample_dir.glob("*.png"))

print(f"Found {len(pages)} sample pages: {[p.name for p in pages]}")
print()

# Process all 4 pages as a single multi-page BMR record
print("=== Record 1: Full 4-page BMR ===")
record1 = orch.process(pages)
print(f"  ID:     {record1.id}")
print(f"  Status: {record1.status.value}")
print(f"  Pages:  {len(record1.pages)}")
print(f"  Fields: {len(record1.current_fields)}")
for f in record1.current_fields:
    print(f"    {f.name:20s} = {f.value:30s}  confidence={f.confidence:.3f}")
print()

# Process pages 1-2 as a separate record
print("=== Record 2: Pages 1-2 ===")
record2 = orch.process(pages[:2])
print(f"  ID:     {record2.id}")
print(f"  Status: {record2.status.value}")
print(f"  Pages:  {len(record2.pages)}")
print(f"  Fields: {len(record2.current_fields)}")
for f in record2.current_fields:
    print(f"    {f.name:20s} = {f.value:30s}  confidence={f.confidence:.3f}")
print()

# Process pages 3-4 as another record
print("=== Record 3: Pages 3-4 ===")
record3 = orch.process(pages[2:])
print(f"  ID:     {record3.id}")
print(f"  Status: {record3.status.value}")
print(f"  Pages:  {len(record3.pages)}")
print(f"  Fields: {len(record3.current_fields)}")
for f in record3.current_fields:
    print(f"    {f.name:20s} = {f.value:30s}  confidence={f.confidence:.3f}")
print()

# Approve record 1 and add to feedback loop
print("=== Approving Record 1 ===")
record1.approve_all_fields()
orch._store.save(record1)
orch._feedback.add_validated_record(record1)
print(f"  All fields approved, saved to store and training dataset")
print()

# Flag record 2 for re-extraction
print("=== Flagging Record 2 for re-extraction ===")
orch._queue.enqueue(record2.id, "batch_number looks wrong, please re-check")
updated = orch.process_reextraction(record2.id)
print(f"  Re-extracted. History entries: {len(updated.extraction_history)}")
print(f"  Current fields: {len(updated.current_fields)}")
print()

# List all records in the store
print("=== All records in store ===")
for s in orch._store.list_records():
    print(f"  {s.id[:12]}…  status={s.status.value:15s}  fields={s.field_count}  avg_conf={s.avg_confidence:.3f}")
