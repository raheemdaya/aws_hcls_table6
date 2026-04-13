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
    if confidence >= 0.8:
        return "green"
    if confidence >= 0.5:
        return "orange"
    return "red"

def _confidence_badge(confidence: float) -> str:
    color = _confidence_color(confidence)
    return f'<span style="color:{color};font-weight:bold;">{confidence:.2f}</span>'

# ---------------------------------------------------------------------------
# Load all records
# ---------------------------------------------------------------------------

summaries = store.list_records()

if not summaries:
    st.info("No records found.")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_review, tab_approved = st.tabs(["📋 Review", "✅ Approved Records"])

# ===========================================================================
# TAB 1: Review
# ===========================================================================

with tab_review:
    # Sidebar – record list (pending/flagged only)
    st.sidebar.header("Records for Review")
    review_summaries = [s for s in summaries if s.status != RecordStatus.APPROVED]

    if not review_summaries:
        st.sidebar.success("All records approved.")
        st.info("No records pending review. Check the Approved Records tab.")
    else:
        for s in review_summaries:
            label = f"{s.id[:8]}… | {s.status.value} | {s.field_count} fields"
            if st.sidebar.button(label, key=f"rec_{s.id}"):
                st.session_state["selected_record_id"] = s.id

        selected_id = st.session_state.get(
            "selected_record_id",
            review_summaries[0].id if review_summaries else None,
        )

        if selected_id is None:
            st.info("Select a record from the sidebar.")
        else:
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

            # Page images
            if record.pages:
                st.markdown("#### Scanned Pages")
                cols = st.columns(min(len(record.pages), 4))
                for idx, page in enumerate(record.pages):
                    col = cols[idx % len(cols)]
                    img_path = Path(page.file_path)
                    if not img_path.exists():
                        col.warning(f"Page {page.page_number} not found")
                    elif img_path.suffix.lower() == ".pdf":
                        with open(img_path, "rb") as f:
                            col.download_button(
                                f"📄 Page {page.page_number} (PDF)",
                                data=f.read(),
                                file_name=page.original_filename,
                                mime="application/pdf",
                                key=f"dl_page_{idx}",
                            )
                    else:
                        try:
                            col.image(str(img_path), caption=f"Page {page.page_number}")
                        except Exception:
                            col.warning(f"Page {page.page_number}: can't display")

            # Extracted fields
            st.markdown("#### Extracted Fields")
            if not record.current_fields:
                st.info("No extracted fields.")
            else:
                for i, field in enumerate(record.current_fields):
                    with st.container():
                        c1, c2, c3, c4 = st.columns([2, 4, 1, 2])
                        c1.markdown(f"**{field.name}**")
                        new_value = c2.text_input(
                            "Value", value=field.value or "", key=f"field_val_{i}",
                            label_visibility="collapsed",
                        )
                        c3.markdown(_confidence_badge(field.confidence), unsafe_allow_html=True)
                        if c4.button("Approve", key=f"approve_field_{i}"):
                            old_value = field.value
                            if new_value != (field.value or ""):
                                field.original_value = field.value
                                field.value = new_value
                                field.status = FieldStatus.EDITED
                                record.reviewer_actions.append(ReviewerAction(
                                    action="edit_field", timestamp=datetime.utcnow(),
                                    field_name=field.name, old_value=old_value, new_value=new_value,
                                ))
                            field.status = FieldStatus.APPROVED
                            record.reviewer_actions.append(ReviewerAction(
                                action="approve_field", timestamp=datetime.utcnow(),
                                field_name=field.name,
                            ))
                            record.updated_at = datetime.utcnow()
                            store.save(record)
                            st.rerun()
                        status_emoji = {FieldStatus.PENDING: "⏳", FieldStatus.APPROVED: "✅", FieldStatus.EDITED: "✏️"}
                        c1.caption(status_emoji.get(field.status, "") + " " + field.status.value)
                    st.divider()

            # Record-level actions
            st.markdown("#### Record Actions")
            col_approve, col_flag = st.columns(2)
            with col_approve:
                if st.button("✅ Approve Entire Record", type="primary"):
                    record.approve_all_fields()
                    record.status = RecordStatus.APPROVED
                    record.reviewer_actions.append(ReviewerAction(
                        action="approve_record", timestamp=datetime.utcnow(),
                    ))
                    record.updated_at = datetime.utcnow()
                    store.save(record)
                    feedback.add_validated_record(record)
                    if feedback.should_retrain():
                        event = feedback.trigger_retrain()
                        st.success(f"Retrain triggered – {event.records_added} new records, {event.total_training_records} total.")
                    st.success("Record approved and added to training dataset.")
                    st.rerun()
            with col_flag:
                notes = st.text_area("Reviewer notes (required to flag)", key="flag_notes", placeholder="Describe the issue…")
                if st.button("🚩 Flag for Re-extraction"):
                    if not notes or not notes.strip():
                        st.error("Reviewer notes are required.")
                    else:
                        record.status = RecordStatus.FLAGGED
                        record.reviewer_actions.append(ReviewerAction(
                            action="flag_record", timestamp=datetime.utcnow(), notes=notes.strip(),
                        ))
                        record.updated_at = datetime.utcnow()
                        store.save(record)
                        queue.enqueue(record.id, notes.strip())
                        st.warning("Record flagged and queued for re-extraction.")
                        st.rerun()

# ===========================================================================
# TAB 2: Approved Records
# ===========================================================================

with tab_approved:
    approved_summaries = [s for s in summaries if s.status == RecordStatus.APPROVED]

    if not approved_summaries:
        st.info("No approved records yet. Approve records from the Review tab.")
    else:
        st.metric("Total Approved", len(approved_summaries))

        # Summary table
        table_data = []
        for s in approved_summaries:
            table_data.append({
                "Record ID": s.id[:12] + "…",
                "Fields": s.field_count,
                "Avg Confidence": f"{s.avg_confidence:.2f}",
                "Created": s.created_at.strftime("%Y-%m-%d %H:%M"),
            })

        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Expandable detail for each approved record
        st.markdown("---")
        for s in approved_summaries:
            with st.expander(f"📄 {s.id[:12]}… — {s.field_count} fields, avg conf {s.avg_confidence:.2f}"):
                try:
                    rec = store.load(s.id)
                except Exception as exc:
                    st.error(f"Failed to load: {exc}")
                    continue

                # Show fields as a clean table
                if rec.current_fields:
                    field_rows = []
                    for f in rec.current_fields:
                        field_rows.append({
                            "Field": f.name,
                            "Value": f.value or "(null)",
                            "Confidence": f"{f.confidence:.2f}",
                            "Status": f.status.value,
                        })
                    st.dataframe(field_rows, use_container_width=True, hide_index=True)

                # Show extraction history count
                if rec.extraction_history:
                    st.caption(f"Extraction attempts: {len(rec.extraction_history) + 1}")

                # Show reviewer actions
                if rec.reviewer_actions:
                    st.caption(f"Reviewer actions: {len(rec.reviewer_actions)}")
