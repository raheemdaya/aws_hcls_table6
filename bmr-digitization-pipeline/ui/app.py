"""Streamlit Review UI for the BMR Digitization Pipeline.

Run with:
    streamlit run ui/app.py

from the bmr-digitization-pipeline/ directory.
"""

import sys
from datetime import datetime
from pathlib import Path

# Allow imports from the src directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st

from bmr_pipeline.config import QUEUE_DIR, RECORDS_DIR, TRAINING_DIR
from bmr_pipeline.feedback import FeedbackLoop
from bmr_pipeline.models import (
    FieldStatus,
    Record,
    RecordStatus,
    ReviewerAction,
)
from bmr_pipeline.queue import ReExtractionQueue
from bmr_pipeline.record_store import RecordStore

# ---------------------------------------------------------------------------
# Initialise shared components (cached across reruns)
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_store() -> RecordStore:
    return RecordStore(storage_dir=RECORDS_DIR)


@st.cache_resource
def _get_queue() -> ReExtractionQueue:
    return ReExtractionQueue(queue_dir=QUEUE_DIR)


@st.cache_resource
def _get_feedback() -> FeedbackLoop:
    return FeedbackLoop(training_dir=TRAINING_DIR)


store = _get_store()
queue = _get_queue()
feedback = _get_feedback()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="BMR Review", layout="wide")
st.title("BMR Record Review")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _confidence_color(confidence: float) -> str:
    """Return a CSS colour string based on confidence thresholds."""
    if confidence >= 0.8:
        return "green"
    if confidence >= 0.5:
        return "orange"
    return "red"


def _confidence_badge(confidence: float) -> str:
    """Return a small coloured HTML badge for a confidence value."""
    color = _confidence_color(confidence)
    return (
        f'<span style="color:{color};font-weight:bold;">'
        f"{confidence:.2f}</span>"
    )


# ---------------------------------------------------------------------------
# Sidebar – record list
# ---------------------------------------------------------------------------

summaries = store.list_records()  # already sorted by created_at desc

st.sidebar.header("Records")

if not summaries:
    st.sidebar.info("No records found.")
    st.stop()

selected_id: str | None = None
for s in summaries:
    label = f"{s.id[:8]}… | {s.status.value} | {s.field_count} fields"
    if st.sidebar.button(label, key=f"rec_{s.id}"):
        st.session_state["selected_record_id"] = s.id

selected_id = st.session_state.get("selected_record_id", summaries[0].id)

# ---------------------------------------------------------------------------
# Load selected record
# ---------------------------------------------------------------------------

try:
    record: Record = store.load(selected_id)
except Exception as exc:
    st.error(f"Failed to load record {selected_id}: {exc}")
    st.stop()

st.subheader(f"Record {record.id[:12]}…")
st.caption(
    f"Status: **{record.status.value}** · "
    f"Created: {record.created_at:%Y-%m-%d %H:%M} · "
    f"Fields: {len(record.current_fields)}"
)

# ---------------------------------------------------------------------------
# Page images
# ---------------------------------------------------------------------------

if record.pages:
    st.markdown("### Scanned Pages")
    cols = st.columns(min(len(record.pages), 4))
    for idx, page in enumerate(record.pages):
        col = cols[idx % len(cols)]
        img_path = Path(page.file_path)
        if img_path.exists():
            col.image(str(img_path), caption=f"Page {page.page_number}")
        else:
            col.warning(f"Page {page.page_number} image not found: {page.file_path}")


# ---------------------------------------------------------------------------
# Extracted fields – editable table with confidence badges
# ---------------------------------------------------------------------------

st.markdown("### Extracted Fields")

if not record.current_fields:
    st.info("No extracted fields for this record.")
else:
    for i, field in enumerate(record.current_fields):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 4, 1, 2])

            c1.markdown(f"**{field.name}**")

            # Inline editing
            new_value = c2.text_input(
                "Value",
                value=field.value or "",
                key=f"field_val_{i}",
                label_visibility="collapsed",
            )

            # Confidence badge (rendered as markdown with HTML)
            c3.markdown(
                _confidence_badge(field.confidence),
                unsafe_allow_html=True,
            )

            # Approve single field
            if c4.button("Approve", key=f"approve_field_{i}"):
                old_value = field.value
                if new_value != (field.value or ""):
                    field.original_value = field.value
                    field.value = new_value
                    field.status = FieldStatus.EDITED
                    record.reviewer_actions.append(
                        ReviewerAction(
                            action="edit_field",
                            timestamp=datetime.utcnow(),
                            field_name=field.name,
                            old_value=old_value,
                            new_value=new_value,
                        )
                    )
                field.status = FieldStatus.APPROVED
                record.reviewer_actions.append(
                    ReviewerAction(
                        action="approve_field",
                        timestamp=datetime.utcnow(),
                        field_name=field.name,
                    )
                )
                record.updated_at = datetime.utcnow()
                store.save(record)
                st.rerun()

            # Show current status chip
            status_emoji = {
                FieldStatus.PENDING: "⏳",
                FieldStatus.APPROVED: "✅",
                FieldStatus.EDITED: "✏️",
            }
            c1.caption(status_emoji.get(field.status, "") + " " + field.status.value)

        st.divider()

# ---------------------------------------------------------------------------
# Record-level actions
# ---------------------------------------------------------------------------

st.markdown("### Record Actions")

col_approve, col_flag = st.columns(2)

# --- Approve entire record ---
with col_approve:
    if st.button("✅ Approve Entire Record", type="primary"):
        record.approve_all_fields()
        record.status = RecordStatus.APPROVED
        record.reviewer_actions.append(
            ReviewerAction(
                action="approve_record",
                timestamp=datetime.utcnow(),
            )
        )
        record.updated_at = datetime.utcnow()
        store.save(record)
        feedback.add_validated_record(record)
        if feedback.should_retrain():
            event = feedback.trigger_retrain()
            st.success(
                f"Retrain triggered – {event.records_added} new records, "
                f"{event.total_training_records} total."
            )
        st.success("Record approved and added to training dataset.")
        st.rerun()

# --- Flag for re-extraction ---
with col_flag:
    notes = st.text_area(
        "Reviewer notes (required to flag)",
        key="flag_notes",
        placeholder="Describe the issue…",
    )
    if st.button("🚩 Flag for Re-extraction"):
        if not notes or not notes.strip():
            st.error("Reviewer notes are required to flag a record for re-extraction.")
        else:
            record.status = RecordStatus.FLAGGED
            record.reviewer_actions.append(
                ReviewerAction(
                    action="flag_record",
                    timestamp=datetime.utcnow(),
                    notes=notes.strip(),
                )
            )
            record.updated_at = datetime.utcnow()
            store.save(record)
            queue.enqueue(record.id, notes.strip())
            st.warning("Record flagged and queued for re-extraction.")
            st.rerun()
