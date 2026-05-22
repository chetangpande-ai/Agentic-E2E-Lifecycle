"""
Requirement analysis display and HITL controls.
"""

import streamlit as st


def render_requirement_view(analyzed_requirements: list):
    """Render analyzed requirements with HITL controls."""
    if not analyzed_requirements:
        st.info("No requirements analyzed yet.")
        return None

    st.markdown("### 🔍 Requirement Analysis Results")

    for idx, item in enumerate(analyzed_requirements):
        req = item.get("requirement", {})
        analysis = item.get("analysis", {})
        score = analysis.get("testability_score", "MEDIUM")
        badge_map = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low"}

        with st.expander(f"**{req.get('id', '')}** — {req.get('title', '')}", expanded=idx == 0):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Priority**: {req.get('priority', 'N/A')} | **Type**: {req.get('issue_type', 'Story')}")
            with col2:
                st.markdown(f'<span class="badge {badge_map.get(score, "badge-medium")}">Testability: {score}</span>', unsafe_allow_html=True)

            if req.get("description"):
                st.markdown(f"**📋 Description**: {req['description'][:500]}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**✅ Functional Requirements**")
                for fr in analysis.get("functional_requirements", []):
                    st.markdown(f"- {fr}")
                st.markdown("**🎯 Test Types**: " + ", ".join([f'`{t}`' for t in analysis.get("recommended_test_types", [])]))
            with c2:
                for gap in analysis.get("acceptance_criteria_gaps", []):
                    st.warning(gap)
                for risk in analysis.get("risks_and_dependencies", []):
                    st.error(risk)

            if analysis.get("summary"):
                st.info(f"**Summary**: {analysis['summary']}")
            st.metric("Estimated Test Cases", analysis.get("estimated_test_cases_count", 0))

    # HITL Controls
    st.markdown("---")
    st.markdown("### 👤 Human Review")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ Approve", key="approve_req", use_container_width=True, type="primary"):
            st.session_state.requirement_decision = "approved"
            return "approved"
    with c2:
        if st.button("❌ Reject", key="reject_req", use_container_width=True):
            st.session_state.requirement_decision = "rejected"
            return "rejected"
    with c3:
        if st.button("🔄 Regenerate", key="regen_req", use_container_width=True):
            st.session_state.show_req_feedback = True

    if st.session_state.get("show_req_feedback"):
        feedback = st.text_area("Feedback for regeneration:", key="req_fb")
        if st.button("Submit & Regenerate", key="submit_req_fb"):
            st.session_state.requirement_decision = "regenerate"
            st.session_state.requirement_feedback = feedback
            st.session_state.show_req_feedback = False
            return "regenerate"
    return None
