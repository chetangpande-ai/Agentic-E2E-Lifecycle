"""
Configuration sidebar component.
Handles Jira connection, GitHub settings, and LLM configuration.
"""

import streamlit as st


def render_sidebar():
    """Render the configuration sidebar."""
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

        # === Jira Configuration ===
        with st.expander("🔗 Jira Configuration", expanded=False):
            jira_url = st.text_input(
                "Jira URL",
                value=st.session_state.get("jira_url", ""),
                placeholder="https://your-domain.atlassian.net",
                key="sidebar_jira_url",
            )
            jira_username = st.text_input(
                "Username/Email",
                value=st.session_state.get("jira_username", ""),
                key="sidebar_jira_username",
            )
            jira_token = st.text_input(
                "API Token",
                type="password",
                value=st.session_state.get("jira_api_token", ""),
                key="sidebar_jira_token",
            )
            jira_project = st.text_input(
                "Project Key",
                value=st.session_state.get("jira_project_key", ""),
                placeholder="PROJ",
                key="sidebar_jira_project",
            )
            jql_filter = st.text_area(
                "JQL Filter",
                value=st.session_state.get("jql_filter", 'issuetype = Story AND status = "To Do"'),
                height=68,
                key="sidebar_jql",
            )

            if st.button("💾 Save Jira Config", key="save_jira", use_container_width=True):
                st.session_state.jira_url = jira_url
                st.session_state.jira_username = jira_username
                st.session_state.jira_api_token = jira_token
                st.session_state.jira_project_key = jira_project
                st.session_state.jql_filter = jql_filter
                st.success("Jira config saved!")

        # === GitHub Configuration ===
        with st.expander("🐙 GitHub Configuration", expanded=False):
            gh_token = st.text_input(
                "Personal Access Token",
                type="password",
                value=st.session_state.get("github_pat", ""),
                key="sidebar_gh_token",
            )
            target_repo = st.text_input(
                "Target Repository",
                value=st.session_state.get("github_target_repo", "chetangpande-ai/HdfcBank-Test-Automation"),
                key="sidebar_target_repo",
            )
            ref_repo = st.text_input(
                "Reference Repository",
                value=st.session_state.get("github_ref_repo", "chetangpande-ai/PW-Automation-Framework"),
                key="sidebar_ref_repo",
            )

            if st.button("💾 Save GitHub Config", key="save_github", use_container_width=True):
                st.session_state.github_pat = gh_token
                st.session_state.github_target_repo = target_repo
                st.session_state.github_ref_repo = ref_repo
                st.success("GitHub config saved!")

        # === LLM Configuration ===
        with st.expander("🤖 LLM Configuration", expanded=False):
            groq_key = st.text_input(
                "Groq API Key",
                type="password",
                value=st.session_state.get("groq_api_key", ""),
                key="sidebar_groq_key",
            )
            model = st.selectbox(
                "Model",
                ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
                index=0,
                key="sidebar_model",
            )
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.05,
                key="sidebar_temp",
            )

            if st.button("💾 Save LLM Config", key="save_llm", use_container_width=True):
                st.session_state.groq_api_key = groq_key
                st.session_state.groq_model = model
                st.session_state.groq_temperature = temperature
                st.success("LLM config saved!")

        # === Target App ===
        with st.expander("🌐 Target Application", expanded=False):
            app_url = st.text_input(
                "Application URL",
                value=st.session_state.get("target_app_url", ""),
                placeholder="https://your-app.com",
                key="sidebar_app_url",
            )
            if st.button("💾 Save", key="save_app", use_container_width=True):
                st.session_state.target_app_url = app_url
                st.success("Target app config saved!")

        st.divider()

        # === Quick Actions ===
        st.markdown("### ⚡ Quick Actions")

        if st.button("🔄 Reset Workflow", key="reset_workflow", use_container_width=True):
            for key in ["workflow_step", "raw_requirements", "analyzed_requirements",
                        "generated_testcases", "generated_scripts", "execution_results",
                        "thread_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.workflow_step = 0
            st.rerun()

        # Status indicator
        st.markdown("---")
        status_color = "🟢" if st.session_state.get("groq_api_key") else "🔴"
        st.markdown(f"{status_color} **LLM**: {'Connected' if st.session_state.get('groq_api_key') else 'Not configured'}")
        jira_status = "🟢" if st.session_state.get("jira_url") else "🔴"
        st.markdown(f"{jira_status} **Jira**: {'Connected' if st.session_state.get('jira_url') else 'Not configured'}")
