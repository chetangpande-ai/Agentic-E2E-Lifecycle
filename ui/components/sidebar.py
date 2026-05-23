"""
Configuration sidebar component.
Reads defaults from session state (pre-populated from .env).
"""

import streamlit as st


def render_sidebar():
    """Render the configuration sidebar with .env pre-populated values."""
    with st.sidebar:
        # Logo/Brand
        st.markdown("""
        <div style="text-align:center; padding: 1rem 0;">
            <h1 style="font-size: 1.5rem; font-weight: 800; 
                background: linear-gradient(135deg, #3b82f6, #8b5cf6, #06b6d4);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; margin: 0;">
                🧪 Agentic QE
            </h1>
            <p style="color: #64748b; font-size: 0.75rem; margin-top: 0.25rem; letter-spacing: 0.05em;">
                STLC LIFECYCLE PLATFORM
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Helper to mask sensitive values
        def mask(val, show=6):
            if not val:
                return "Not configured"
            return val[:show] + "•" * min(len(val) - show, 20)

        # === Connection Status Panel ===
        st.markdown("### 🔌 Connections")

        # Jira
        jira_url = st.session_state.get("jira_url", "")
        jira_proj = st.session_state.get("jira_project_key", "")
        if jira_url:
            st.markdown(f"🟢 **Jira** — `{jira_proj}`")
            st.caption(f"{jira_url}")
        else:
            st.markdown("🔴 **Jira** — Not configured")

        # Groq
        groq_key = st.session_state.get("groq_api_key", "")
        groq_model = st.session_state.get("groq_model", "")
        if groq_key:
            st.markdown(f"🟢 **LLM** — `{groq_model}`")
            st.caption(f"Key: {mask(groq_key)}")
        else:
            st.markdown("🔴 **LLM** — Not configured")

        # GitHub
        gh_pat = st.session_state.get("github_pat", "")
        gh_target = st.session_state.get("github_target_repo", "")
        gh_ref = st.session_state.get("github_ref_repo", "")
        if gh_pat:
            st.markdown(f"🟢 **GitHub**")
            st.caption(f"Target: {gh_target}")
            st.caption(f"Ref: {gh_ref}")
        else:
            st.markdown("🔴 **GitHub** — Not configured")

        # Target App
        target_url = st.session_state.get("target_app_url", "")
        if target_url:
            st.markdown(f"🟢 **Target App**")
            st.caption(f"{target_url}")
        else:
            st.markdown("⚪ **Target App** — Not set")

        st.divider()

        # === Detailed Config (Read-only expandable) ===
        with st.expander("📋 Configuration Details", expanded=False):
            st.markdown("**Jira**")
            st.text(f"URL: {jira_url or 'N/A'}")
            st.text(f"User: {st.session_state.get('jira_username', 'N/A')}")
            st.text(f"Project: {jira_proj or 'N/A'}")
            st.text(f"JQL: {st.session_state.get('jql_filter', 'N/A')}")

            st.markdown("**LLM**")
            st.text(f"Model: {groq_model or 'N/A'}")

            st.markdown("**GitHub**")
            st.text(f"Target: {gh_target or 'N/A'}")
            st.text(f"Reference: {gh_ref or 'N/A'}")

            st.markdown("**Target App**")
            st.text(f"URL: {target_url or 'N/A'}")

            st.info("💡 Edit `.env` file to change configuration")

        st.divider()

        # === Quick Actions ===
        st.markdown("### ⚡ Quick Actions")

        if st.button("🔄 Reset Workflow", key="reset_workflow", use_container_width=True):
            keys_to_reset = [
                "workflow_step", "raw_requirements", "analyzed_requirements",
                "generated_testcases", "generated_scripts", "execution_results",
                "thread_id", "script_dependencies", "script_setup_commands",
                "pr_url", "rejected_step", "messages",
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.workflow_step = 0
            st.session_state.rejected_step = -1
            st.session_state.messages = []
            st.rerun()
