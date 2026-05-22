"""
Execution results display with auto-heal tracking and PR link.
"""

import streamlit as st


def render_execution_view(execution_results: list, pr_url: str = ""):
    """Render test execution results with detailed logs."""
    if not execution_results:
        st.info("No execution results yet.")
        return

    st.markdown("### 🚀 Test Execution Results")

    for result in execution_results:
        status = result.get("status", "ERROR")
        color = {"PASS": "🟢", "FAIL": "🔴", "ERROR": "🟠"}.get(status, "⚪")

        st.markdown(f"## {color} Status: **{status}**")

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Tests", result.get("total_tests", 0))
        with c2:
            st.metric("Passed", result.get("passed", 0))
        with c3:
            st.metric("Failed", result.get("failed", 0))
        with c4:
            st.metric("Auto-Heal Attempts", len(result.get("auto_heal_attempts", [])))

        # Individual test results
        for tr in result.get("results", []):
            tr_status = tr.get("status", "ERROR")
            icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(tr_status, "⚠️")
            with st.expander(f"{icon} {tr.get('test_name', 'Test')} — {tr_status}"):
                if tr.get("error_message"):
                    st.error(tr["error_message"])
                if tr.get("stack_trace"):
                    st.code(tr["stack_trace"][:1000], language="text")

        # Auto-heal history
        heals = result.get("auto_heal_attempts", [])
        if heals:
            st.markdown("#### 🔧 Auto-Heal History")
            for h in heals:
                icon = "✅" if h.get("success") else "❌"
                st.markdown(
                    f"**Attempt {h.get('attempt_number', '?')}** {icon}\n"
                    f"- Root Cause: {h.get('root_cause', 'N/A')}\n"
                    f"- Fix: {h.get('fix_description', 'N/A')}"
                )

        # Logs
        if result.get("logs"):
            with st.expander("📋 Execution Logs"):
                st.code(result["logs"][:3000], language="text")

    # PR Link
    if pr_url:
        st.success(f"🎉 **Pull Request Created**: [{pr_url}]({pr_url})")
        st.balloons()
