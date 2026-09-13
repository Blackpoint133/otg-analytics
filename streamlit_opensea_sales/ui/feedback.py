"""Feedback submission page."""
from datetime import datetime, timedelta, timezone
import uuid
from urllib.parse import urlencode
import streamlit as st

from feedback_store import insert_feedback, sanitize_source_item
from feedback_notifications import send_feedback_notification


def _context():
    raw_source = st.query_params.get("source", "unknown")
    if isinstance(raw_source, list):
        raw_source = raw_source[0] if raw_source else "unknown"
    source = str(raw_source or "unknown").strip().lower()
    if source == "top_traders":
        source = "trader"
    if source not in {"item", "market", "top_items", "top_traders", "trader", "roadmap"}:
        source = "unknown"
    item = sanitize_source_item(st.query_params.get("item")) if source == "item" else None
    return source, item


def _source_label(source):
    return {"item": "ITEM ANALYTICS", "market": "MARKET", "top_items": "TOP ITEMS", "top_traders": "TOP TRADERS", "trader": "TOP TRADERS", "roadmap": "ROADMAP"}.get(source, "UNKNOWN")


def _back_target(source, item):
    mode = {"item": "item", "market": "market", "top_items": "top_items", "top_traders": "top_traders", "trader": "top_traders", "roadmap": "roadmap"}.get(source, "item")
    params = {"mode": mode}
    if source == "item" and item:
        params["item"] = item
    return "/?" + urlencode(params)


def _back_label(source):
    return {"item": "ITEM ANALYTICS", "market": "MARKET", "top_items": "TOP ITEMS", "trader": "TOP TRADERS", "roadmap": "ROADMAP"}.get(source, "ANALYTICS")


def render_feedback_page() -> None:
    source, item = _context()
    with st.container(key="feedback_page"):
        st.markdown("""<style>
.st-key-feedback_page{width:100%;max-width:800px;margin:0;padding:0}.st-key-feedback_page h1{margin:0 0 12px}.st-key-feedback_page .feedback-subtitle{color:#FF003A;font-weight:700;letter-spacing:1px;margin:0 0 14px}.st-key-feedback_page [data-testid="stForm"]{width:100%;box-sizing:border-box;background:#050505;border:1px solid #303035;border-radius:0;padding:20px}.st-key-feedback_page [data-testid="stFormSubmitButton"] button{width:200px;height:38px;background:#FF003A;color:#FFF;border:1px solid #FF003A;border-radius:0;font-weight:700}.st-key-feedback_page [data-testid="stFormSubmitButton"] button:hover{background:#E60033;border-color:#E60033}.st-key-feedback_page .feedback-back{display:inline-flex;align-items:center;height:32px;padding:0 12px;margin:0 0 20px;background:#050505;border:1px solid #303035;color:#FFF;text-decoration:none;font-size:10px;font-weight:700;letter-spacing:.8px}.st-key-feedback_page .feedback-back:hover,.st-key-feedback_page .feedback-back:focus{border-color:#FF003A;color:#FF003A}@media(max-width:768px){.st-key-feedback_page{width:100%;max-width:100%}.st-key-feedback_page [data-testid="stForm"]{padding:14px}.st-key-feedback_page [data-testid="stFormSubmitButton"] button{width:100%}}
</style>""", unsafe_allow_html=True)
        st.markdown(f'<a class="feedback-back" href="{_back_target(source, item)}">← BACK TO {_back_label(source)}</a>', unsafe_allow_html=True)
        st.markdown("<h1>FEEDBACK</h1><p class='feedback-subtitle'>HELP IMPROVE OTG ANALYTICS</p><p>Found a bug, incorrect data, or have an idea?<br>Send it here. Context about the page you came from is attached automatically.</p>", unsafe_allow_html=True)
        labels = {"BUG": "bug", "SUGGESTION": "suggestion", "DATA ISSUE": "data_issue", "OTHER": "other"}
        with st.form("feedback_form"):
            feedback_label = st.selectbox("TYPE", list(labels), label_visibility="visible")
            message = st.text_area("MESSAGE", placeholder="Describe the issue or idea...", height=180)
            st.markdown("**ATTACHED CONTEXT**")
            st.markdown(f"**SOURCE PAGE**\n\n{_source_label(source)}")
            if item:
                st.markdown(f"**ITEM**\n\n{item}")
            st.caption("This context is attached automatically to help reproduce your report.")
            st.caption("Do not include passwords, seed phrases, private keys, or other sensitive information.")
            submitted = st.form_submit_button("SEND FEEDBACK")
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
            if result == "inserted":
                try:
                    send_feedback_notification(
                        submission_id=submission_id,
                        feedback_type=labels[feedback_label],
                        message=clean_message,
                        source_mode=source,
                        source_item_key=item,
                    )
                except Exception:
                    pass
            st.session_state.feedback_successes = [*timestamps, now]
            st.session_state.feedback_submission_id = uuid.uuid4()
            st.success("FEEDBACK RECEIVED")
            st.caption("Thanks — your message was saved.")
        else:
            st.error("FEEDBACK COULD NOT BE SENT")
            st.caption("Please try again later.")
