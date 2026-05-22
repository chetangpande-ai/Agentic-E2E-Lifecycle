"""
Test case display and HITL controls.
"""

import streamlit as st


def render_testcase_view(test_cases: list):
    """Render generated test cases with HITL controls."""
    if not test_cases:
        st.info("No test cases generated yet.")
        return None

    st.markdown(f"### 📝 Generated Test Cases ({len(test_cases)})")

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    types = [tc.get("test_type", "UI") for tc in test_cases]
    with c1:
        st.metric("Total", len(test_cases))
    with c2:
        st.metric("UI Tests", types.count("UI"))
    with c3:
        st.metric("API Tests", types.count("API"))
    with c4:
        st.metric("Other", len(test_cases) - types.count("UI") - types.count("API"))

    for tc in test_cases:
        priority = tc.get("priority", "P2")
        pclass = f"badge-{priority.lower()}"
        tclass = f"badge-{tc.get('test_type', 'UI').lower()}"

        with st.expander(f"**{tc.get('id', '')}** — {tc.get('title', '')}"):
            st.markdown(
                f'<span class="badge {pclass}">{priority}</span> '
                f'<span class="badge {tclass}">{tc.get("test_type", "UI")}</span>',
                unsafe_allow_html=True,
            )

            if tc.get("description"):
                st.markdown(f"_{tc['description']}_")

            if tc.get("preconditions"):
                st.markdown("**Preconditions**")
                for pre in tc["preconditions"]:
                    st.markdown(f"- {pre}")

            st.markdown("**Test Steps**")
            steps = tc.get("steps", [])
            for step in steps:
                st.markdown(
                    f"**Step {step.get('step_number', '?')}**: {step.get('action', '')}\n"
                    f"- Input: `{step.get('input_data', '-')}`\n"
                    f"- Expected: _{step.get('expected_result', '-')}_"
                )

            if tc.get("test_data"):
                st.json(tc["test_data"])

            if tc.get("tags"):
                st.markdown("**Tags**: " + " ".join([f'`{t}`' for t in tc["tags"]]))

    # HITL Controls
    st.markdown("---")
    st.markdown("### 👤 Human Review")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ Approve", key="approve_tc", use_container_width=True, type="primary"):
            st.session_state.testcase_decision = "approved"
            return "approved"
    with c2:
        if st.button("❌ Reject", key="reject_tc", use_container_width=True):
            st.session_state.testcase_decision = "rejected"
            return "rejected"
    with c3:
        if st.button("🔄 Regenerate", key="regen_tc", use_container_width=True):
            st.session_state.show_tc_feedback = True

    if st.session_state.get("show_tc_feedback"):
        feedback = st.text_area("Feedback for regeneration:", key="tc_fb")
        if st.button("Submit & Regenerate", key="submit_tc_fb"):
            st.session_state.testcase_decision = "regenerate"
            st.session_state.testcase_feedback = feedback
            st.session_state.show_tc_feedback = False
            return "regenerate"
    return None
