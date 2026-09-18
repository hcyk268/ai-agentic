from __future__ import annotations

import streamlit as st

from issue_triage.config import base_url, model_name, openai_client
from issue_triage.models import IssueTriage, TriageRun
from issue_triage.prompts import DEFAULT_ISSUE
from issue_triage.service import triage_issue

st.set_page_config(
    page_title="Issue Triage — BTVN #1",
    page_icon="IT",
    layout="wide",
)


def render_summary(triage: IssueTriage) -> None:
    """Render the validated IssueTriage result."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", triage.status)
    col2.metric("Severity", triage.severity or "—")
    col3.metric("Component", triage.component or "—")
    col4.metric("Urgent", "YES" if triage.needs_urgent_response else "NO")

    st.subheader("Reason")
    st.write(triage.reason)


def render_trace(result: TriageRun) -> None:
    """Render tool_call → execute → tool_result trace."""
    with st.expander("Trace function calling", expanded=True):
        for index, trace in enumerate(result.tool_traces, start=1):
            st.markdown(f"### {index}. tool_call")
            st.json(
                {
                    "id": trace.call_id,
                    "name": trace.name,
                    "arguments": trace.arguments,
                }
            )
            st.markdown("### application executes")
            st.code(
                f"get_component_owner({trace.arguments['component']!r})"
                f" -> {trace.result['owner']!r}"
            )
            st.markdown("### tool_result")
            st.json(trace.result)

    st.subheader("Final response — IssueTriage")
    st.json(result.triage.model_dump())


def main() -> None:
    st.title("Issue Triage mini-app")
    st.caption("prompt template → tool calling → application validation → IssueTriage")

    with st.sidebar:
        st.header("Runtime")
        st.write("Base URL")
        st.code(base_url())
        st.write("Model")
        st.code(model_name())

    with st.form("triage_form"):
        issue = st.text_area(
            "Mô tả issue",
            value=DEFAULT_ISSUE,
            height=220,
            help="Nêu symptom, phạm vi ảnh hưởng và thời điểm nếu có.",
        )
        submitted = st.form_submit_button(
            "Phân loại issue",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return
    if not issue.strip():
        st.error("Issue không được để trống.")
        return

    try:
        with st.spinner("Đang gọi model và chạy tool..."):
            result = triage_issue(openai_client(), model_name(), issue)
    except Exception as exc:
        st.error(f"Triage thất bại: {type(exc).__name__}: {exc}")
        return

    st.success("Đã hoàn tất flow.")
    render_summary(result.triage)
    render_trace(result)


if __name__ == "__main__":
    main()
