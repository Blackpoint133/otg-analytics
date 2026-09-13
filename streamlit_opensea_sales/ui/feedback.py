"""Feedback submission page."""
from datetime import datetime, timedelta, timezone
import uuid
import streamlit as st

from feedback_store import insert_feedback, normalize_source_mode, sanitize_source_item


def _context():
    source = normalize_source_mode(st.query_params.get("source", "unknown"))
    item = sanitize_source_item(st.query_params.get("item")) if source == "item" else None
    return source, item


def render_feedback_page() -> None:
    source, item = _context()
    st.markdown("<div class='feedback-page'><h1>FEEDBACK</h1><p class='feedback-subtitle'>HELP IMPROVE OTG ANALYTICS</p><p>Found a bug, incorrect data, or have an idea?<br>Send it here. Context about the page you came from is attached automatically.</p>", unsafe_allow_html=True)
    st.markdown("""<style>
.feedback-page{max-width:760px;margin:0;padding:0}.feedback-panel{background:#050505;border:1px solid #303035;border-radius:0;padding:20px}.feedback-subtitle{color:#FF003A;font-weight:700;letter-spacing:1px}.feedback-context{color:#C8C8C8;font-size:12px;margin:8px 0 16px}.feedback-warning{color:#77777d;font-size:11px}.feedback-page [data-testid="stFormSubmitButton"] button{background:#FF003A;color:#FFF;border:1px solid #FF003A;border-radius:0;font-weight:700}@media(max-width:768px){.feedback-panel{padding:14px}.feedback-page{width:100%}}
</style><div class='feedback-panel'>""", unsafe_allow_html=True)
    labels = {"BUG": "bug", "SUGGESTION": "suggestion", "DATA ISSUE": "data_issue", "OTHER": "other"}
    with st.form("feedback_form"):
        feedback_label = st.selectbox("TYPE", list(labels), label_visibility="visible")
        message = st.text_area("MESSAGE", placeholder="Describe the issue or idea...", height=180)
        context_text = f"{source.upper()}" + (f"  {item}" if item else "")
        st.markdown(f"**CONTEXT**\n\n{context_text}")
        st.caption("Do not include passwords, seed phrases, private keys, or other sensitive information.")
        submitted = st.form_submit_button("SEND FEEDBACK")
    st.markdown("</div></div>", unsafe_allow_html=True)
    if not submitted:
        return
    clean_message = message.strip()
    if not 10 <= len(clean_message) <= 2000:
        st.error("MESSAGE must be between 10 and 2000 characters.")
        return
    now = datetime.now(timezone.utc)
    timestamps = [t for t in st.session_state.get("feedback_successes", []) if now - t < timedelta(minutes=10)]
    st.session_state.feedback_successes = timestamps
    if len(timestamps) >= 5:
        st.warning("TOO MANY SUBMISSIONS")
        st.caption("Please wait a few minutes and try again.")
        return
    submission_id = st.session_state.get("feedback_submission_id") or uuid.uuid4()
    st.session_state.feedback_submission_id = submission_id
    try:
        result = insert_feedback(submission_id=submission_id, feedback_type=labels[feedback_label], message=clean_message, source_mode=source, source_item_key=item, source_context={"source_mode": source, "item": item})
    except Exception:
        st.error("FEEDBACK COULD NOT BE SENT")
        st.caption("Please try again later.")
        return
    if result in ("inserted", "duplicate"):
        st.session_state.feedback_successes = [*timestamps, now]
        st.session_state.feedback_submission_id = uuid.uuid4()
        st.success("FEEDBACK RECEIVED")
        st.caption("Thanks — your message was saved.")
    else:
        st.error("FEEDBACK COULD NOT BE SENT")
        st.caption("Please try again later.")
