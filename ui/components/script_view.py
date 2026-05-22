"""
Script display with code viewer and HITL controls.
"""

import streamlit as st


def render_script_view(scripts: list, dependencies: list = None, setup_commands: list = None):
    """Render generated scripts with syntax-highlighted code viewer."""
    if not scripts:
        st.info("No scripts generated yet.")
        return None

    st.markdown(f"### 💻 Generated Test Scripts ({len(scripts)} files)")

    # File tree
    st.markdown("**📁 File Structure**")
    for f in scripts:
        icon = {"feature": "📄", "step_definition": "⚙️", "page_object": "🏗️", "config": "⚙️"}.get(f.get("file_type", ""), "📄")
        st.markdown(f"  {icon} `{f.get('path', '')}`")

    if dependencies:
        st.markdown("**📦 Dependencies**: " + ", ".join([f'`{d}`' for d in dependencies]))

    if setup_commands:
        st.markdown("**🔧 Setup Commands**")
        for cmd in setup_commands:
            st.code(cmd, language="bash")

    st.markdown("---")

    # Code viewer with tabs
    if scripts:
        tab_names = [f.get("path", f"File {i}").split("/")[-1] for i, f in enumerate(scripts)]
        tabs = st.tabs(tab_names)

        for i, (tab, script) in enumerate(zip(tabs, scripts)):
            with tab:
                path = script.get("path", "")
                lang = "gherkin" if path.endswith(".feature") else "typescript"
                st.code(script.get("content", ""), language=lang)

    # HITL Controls
    st.markdown("---")
    st.markdown("### 👤 Human Review")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ Approve", key="approve_sc", use_container_width=True, type="primary"):
            st.session_state.script_decision = "approved"
            return "approved"
    with c2:
        if st.button("❌ Reject", key="reject_sc", use_container_width=True):
            st.session_state.script_decision = "rejected"
            return "rejected"
    with c3:
        if st.button("🔄 Regenerate", key="regen_sc", use_container_width=True):
            st.session_state.show_sc_feedback = True

    if st.session_state.get("show_sc_feedback"):
        feedback = st.text_area("Feedback for regeneration:", key="sc_fb")
        if st.button("Submit & Regenerate", key="submit_sc_fb"):
            st.session_state.script_decision = "regenerate"
            st.session_state.script_feedback = feedback
            st.session_state.show_sc_feedback = False
            return "regenerate"
    return None
