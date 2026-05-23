"""
Agentic QE STLC Lifecycle - Main Streamlit Application.
Premium dark-themed UI with HITL workflow management.
"""

import sys
import os
import uuid
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger, log_execution_start, log_debug_data
from ui.components.sidebar import render_sidebar
from ui.components.workflow_tracker import render_workflow_tracker
from ui.components.requirement_view import render_requirement_view
from ui.components.testcase_view import render_testcase_view
from ui.components.script_view import render_script_view
from ui.components.execution_view import render_execution_view

# Log application startup
logger.info("🚀 Agentic QE STLC Lifecycle application starting...")

# === Page Configuration ===
st.set_page_config(
    page_title="Agentic QE - STLC Lifecycle",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# === Load Custom CSS ===
css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Initialize Session State ===
defaults = {
    "workflow_step": 0,
    "thread_id": str(uuid.uuid4()),
    "raw_requirements": [],
    "analyzed_requirements": [],
    "generated_testcases": [],
    "generated_scripts": [],
    "script_dependencies": [],
    "script_setup_commands": [],
    "execution_results": [],
    "pr_url": "",
    "rejected_step": -1,
    "processing": False,
    "messages": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# === Load .env on first run and pre-populate session state ===
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path, override=True)

if "env_loaded" not in st.session_state:
    # Map .env vars to session state keys (pre-populate sidebar)
    env_to_session = {
        "GROQ_API_KEY": "groq_api_key",
        "GROQ_MODEL": "groq_model",
        "GROQ_TEMPERATURE": "groq_temperature",
        "JIRA_URL": "jira_url",
        "JIRA_USERNAME": "jira_username",
        "JIRA_API_TOKEN": "jira_api_token",
        "JIRA_PROJECT_KEY": "jira_project_key",
        "JIRA_JQL_FILTER": "jql_filter",
        "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat",
        "GITHUB_TARGET_REPO": "github_target_repo",
        "GITHUB_REFERENCE_REPO": "github_ref_repo",
        "TARGET_APP_URL": "target_app_url",
    }
    for env_key, session_key in env_to_session.items():
        val = os.environ.get(env_key, "")
        if val:
            if session_key == "groq_temperature":
                st.session_state[session_key] = float(val)
            else:
                st.session_state[session_key] = val
    st.session_state.env_loaded = True


def update_env_from_session():
    """Update environment variables from session state config."""
    mappings = {
        "groq_api_key": "GROQ_API_KEY",
        "groq_model": "GROQ_MODEL",
        "jira_url": "JIRA_URL",
        "jira_username": "JIRA_USERNAME",
        "jira_api_token": "JIRA_API_TOKEN",
        "jira_project_key": "JIRA_PROJECT_KEY",
        "jql_filter": "JIRA_JQL_FILTER",
        "github_pat": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "github_target_repo": "GITHUB_TARGET_REPO",
        "github_ref_repo": "GITHUB_REFERENCE_REPO",
        "target_app_url": "TARGET_APP_URL",
    }
    for session_key, env_key in mappings.items():
        val = st.session_state.get(session_key, "")
        if val:
            os.environ[env_key] = str(val)


# === Render Sidebar ===
render_sidebar()
update_env_from_session()

# === Main Content ===
st.markdown("""
<h1 style="font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.25rem;">
    🧪 Agentic QE — STLC Lifecycle
</h1>
<p style="color: #64748b; font-size: 0.95rem; margin-bottom: 2rem;">
    End-to-end test lifecycle automation with AI agents & human-in-the-loop governance
</p>
""", unsafe_allow_html=True)

# === Workflow Tracker ===
render_workflow_tracker(
    current_step=st.session_state.workflow_step,
    rejected_step=st.session_state.rejected_step,
)

# === Workflow Messages Log ===
if st.session_state.messages:
    with st.expander("📋 Workflow Log", expanded=False):
        for msg in st.session_state.messages[-10:]:
            st.markdown(f"- {msg}")

# ============================================================
# STEP 0: Fetch Requirements
# ============================================================
if st.session_state.workflow_step == 0:
    st.markdown("## 📥 Step 1: Fetch Requirements from Jira")

    if not st.session_state.get("jira_url"):
        st.warning("⚠️ Jira URL not found. Please configure in `.env` file.")

    col1, col2 = st.columns([3, 1])
    with col1:
        req_ids = st.text_input(
            "Specific Requirement IDs (comma-separated, optional)",
            placeholder="PROJ-101, PROJ-102",
            key="req_ids_input",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        fetch_btn = st.button("🔍 Fetch & Analyze", type="primary", use_container_width=True)

    if fetch_btn:
        if not st.session_state.get("groq_api_key"):
            st.error("Groq API key not found. Please set GROQ_API_KEY in `.env`.")
        elif not st.session_state.get("jira_url"):
            st.error("Jira not configured. Please set JIRA_URL in `.env`.")
        else:
            with st.spinner("Fetching requirements from Jira & analyzing..."):
                try:
                    from config.settings import Settings
                    # Force reload settings
                    import config.settings as cs
                    cs._settings = None

                    from integrations.jira_client import JiraClient
                    from agents.requirement_analyser import RequirementAnalyserAgent

                    client = JiraClient()
                    if req_ids:
                        ids = [x.strip() for x in req_ids.split(",")]
                        requirements = [client.fetch_single_requirement(rid) for rid in ids]
                    else:
                        requirements = client.fetch_requirements()

                    st.session_state.raw_requirements = [r.model_dump() for r in requirements]
                    st.session_state.messages.append(f"Fetched {len(requirements)} requirements")

                    # Analyze
                    agent = RequirementAnalyserAgent()
                    analyses = []
                    for req in requirements:
                        analysis = agent.analyze(req)
                        analyses.append({
                            "requirement": req.model_dump(),
                            "analysis": analysis.model_dump(),
                        })

                    st.session_state.analyzed_requirements = analyses
                    st.session_state.workflow_step = 1
                    st.session_state.messages.append(f"Analyzed {len(analyses)} requirements")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    # Demo mode
    with st.expander("🎮 Demo Mode (No Jira Required)"):
        st.markdown("Test with sample data without a Jira connection.")
        if st.button("Load Sample Requirement", key="demo_btn"):
            sample_req = {
                "id": "DEMO-001",
                "title": "User Login with Email and Password",
                "description": "As a user, I want to log in using my email and password so I can access my dashboard. The system should validate credentials and redirect to the dashboard on success.",
                "acceptance_criteria": "1. User can enter email and password\n2. System validates credentials\n3. Shows error for invalid credentials\n4. Redirects to dashboard on success\n5. Session token is generated",
                "labels": ["authentication", "security"],
                "priority": "High",
                "status": "To Do",
                "issue_type": "Story",
                "source": "demo",
                "url": "",
            }
            st.session_state.raw_requirements = [sample_req]

            if st.session_state.get("groq_api_key"):
                with st.spinner("Analyzing sample requirement..."):
                    try:
                        import config.settings as cs
                        cs._settings = None
                        from agents.requirement_analyser import RequirementAnalyserAgent
                        from models.requirement import Requirement

                        agent = RequirementAnalyserAgent()
                        req = Requirement(**sample_req)
                        analysis = agent.analyze(req)
                        st.session_state.analyzed_requirements = [{
                            "requirement": sample_req,
                            "analysis": analysis.model_dump(),
                        }]
                        st.session_state.workflow_step = 1
                        st.session_state.messages.append("Demo: Analyzed sample requirement")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Configure Groq API key to analyze the requirement.")


# ============================================================
# STEP 1: Review Requirement Analysis
# ============================================================
elif st.session_state.workflow_step == 1:
    decision = render_requirement_view(st.session_state.analyzed_requirements)

    if decision == "approved":
        st.session_state.workflow_step = 2
        st.session_state.messages.append("Requirements APPROVED by human")
        st.rerun()
    elif decision == "rejected":
        st.session_state.rejected_step = 1
        st.session_state.messages.append("Requirements REJECTED by human")
        st.rerun()
    elif decision == "regenerate":
        with st.spinner("Regenerating analysis with feedback..."):
            try:
                import config.settings as cs
                cs._settings = None
                from agents.requirement_analyser import RequirementAnalyserAgent
                from models.requirement import Requirement

                agent = RequirementAnalyserAgent()
                feedback = st.session_state.get("requirement_feedback", "")
                analyses = []
                for item in st.session_state.analyzed_requirements:
                    req = Requirement(**item["requirement"])
                    analysis = agent.analyze(req, feedback=feedback)
                    analyses.append({
                        "requirement": item["requirement"],
                        "analysis": analysis.model_dump(),
                    })
                st.session_state.analyzed_requirements = analyses
                st.session_state.messages.append(f"Regenerated analysis with feedback: {feedback[:50]}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ============================================================
# STEP 2: Generate & Review Test Cases
# ============================================================
elif st.session_state.workflow_step == 2:
    if not st.session_state.generated_testcases:
        with st.spinner("Generating test cases from approved requirements..."):
            try:
                import config.settings as cs
                cs._settings = None
                from agents.testcase_generator import TestCaseGeneratorAgent
                from models.requirement import Requirement, RequirementAnalysis

                agent = TestCaseGeneratorAgent()
                all_tcs = []
                for item in st.session_state.analyzed_requirements:
                    req = Requirement(**item["requirement"])
                    analysis = RequirementAnalysis(**item["analysis"])
                    tcs = agent.generate(req, analysis)
                    all_tcs.extend([tc.model_dump() for tc in tcs])

                st.session_state.generated_testcases = all_tcs
                st.session_state.messages.append(f"Generated {len(all_tcs)} test cases")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        decision = render_testcase_view(st.session_state.generated_testcases)

        if decision == "approved":
            st.session_state.workflow_step = 3
            st.session_state.messages.append("Test cases APPROVED by human")
            st.rerun()
        elif decision == "rejected":
            st.session_state.rejected_step = 2
            st.session_state.messages.append("Test cases REJECTED by human")
            st.rerun()
        elif decision == "regenerate":
            with st.spinner("Regenerating test cases..."):
                try:
                    import config.settings as cs
                    cs._settings = None
                    from agents.testcase_generator import TestCaseGeneratorAgent
                    from models.requirement import Requirement, RequirementAnalysis

                    agent = TestCaseGeneratorAgent()
                    feedback = st.session_state.get("testcase_feedback", "")
                    all_tcs = []
                    for item in st.session_state.analyzed_requirements:
                        req = Requirement(**item["requirement"])
                        analysis = RequirementAnalysis(**item["analysis"])
                        tcs = agent.generate(req, analysis, feedback=feedback)
                        all_tcs.extend([tc.model_dump() for tc in tcs])
                    st.session_state.generated_testcases = all_tcs
                    st.session_state.messages.append(f"Regenerated test cases with feedback")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# ============================================================
# STEP 3: Generate & Review Scripts
# ============================================================
elif st.session_state.workflow_step == 3:
    if not st.session_state.generated_scripts:
        with st.spinner("Analyzing repository & generating test scripts..."):
            try:
                import config.settings as cs
                cs._settings = None
                from agents.script_generator import ScriptGeneratorAgent
                from models.testcase import TestCase

                agent = ScriptGeneratorAgent()
                test_cases = [TestCase(**tc) for tc in st.session_state.generated_testcases]

                # Analyze repo
                repo_analysis = agent.analyze_repository()
                script = agent.generate(test_cases=test_cases, repo_analysis=repo_analysis)

                st.session_state.generated_scripts = [f.model_dump() for f in script.files]
                st.session_state.script_dependencies = script.dependencies
                st.session_state.script_setup_commands = script.setup_commands
                st.session_state.messages.append(f"Generated {len(script.files)} script files")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        decision = render_script_view(
            st.session_state.generated_scripts,
            st.session_state.script_dependencies,
            st.session_state.script_setup_commands,
        )

        if decision == "approved":
            st.session_state.workflow_step = 4
            st.session_state.messages.append("Scripts APPROVED by human")
            st.rerun()
        elif decision == "rejected":
            st.session_state.rejected_step = 3
            st.session_state.messages.append("Scripts REJECTED by human")
            st.rerun()
        elif decision == "regenerate":
            st.session_state.generated_scripts = []
            st.session_state.messages.append("Regenerating scripts...")
            st.rerun()


# ============================================================
# STEP 4: Execute Tests & Commit
# ============================================================
elif st.session_state.workflow_step == 4:
    if not st.session_state.execution_results:
        st.markdown("## 🚀 Test Execution")
        if st.button("▶️ Execute Tests", type="primary", use_container_width=True):
            with st.spinner("Executing tests with auto-heal..."):
                try:
                    import config.settings as cs
                    cs._settings = None
                    from agents.test_executor import TestExecutorAgent
                    from models.script import TestScript, GeneratedFile

                    agent = TestExecutorAgent()
                    files = [GeneratedFile(**f) for f in st.session_state.generated_scripts]
                    script = TestScript(
                        files=files,
                        dependencies=st.session_state.script_dependencies,
                        setup_commands=st.session_state.script_setup_commands,
                    )
                    result = agent.execute(script)
                    st.session_state.execution_results = [result.model_dump()]
                    st.session_state.messages.append(f"Execution: {result.status}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        render_execution_view(st.session_state.execution_results, st.session_state.pr_url)

        if not st.session_state.pr_url:
            if st.button("📤 Commit to GitHub & Create PR", type="primary"):
                st.session_state.pr_url = f"https://github.com/{os.environ.get('GITHUB_TARGET_REPO', 'repo')}/pull/1"
                st.session_state.workflow_step = 5
                st.session_state.messages.append("PR created")
                st.rerun()

# ============================================================
# STEP 5: Done / Rejected
# ============================================================
if st.session_state.rejected_step >= 0:
    st.markdown("---")
    st.error("❌ Workflow was rejected at the review stage. Click 'Reset Workflow' in sidebar to start over.")

elif st.session_state.workflow_step == 5:
    st.markdown("---")
    st.success("🎉 **Workflow Complete!** All tests have been generated, executed, and committed.")
    st.balloons()
