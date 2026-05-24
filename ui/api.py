"""
FastAPI backend for the React UI.

The API keeps the existing agent workflow intact while replacing Streamlit
session state with a small in-memory workflow state.
"""

from __future__ import annotations

import os
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env", override=True)


def _initial_state() -> dict[str, Any]:
    return {
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


STATE: dict[str, Any] = _initial_state()

app = FastAPI(title="Agentic QE UI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FetchRequirementsRequest(BaseModel):
    requirement_ids: str = ""


class FeedbackRequest(BaseModel):
    feedback: str = ""


def _reset_settings() -> None:
    import config.settings as cs

    cs._settings = None


def _serialize_state() -> dict[str, Any]:
    return deepcopy(STATE)


def _append_message(message: str) -> None:
    STATE["messages"].append(message)


def _require_config(*keys: str) -> None:
    missing = [key for key in keys if not os.environ.get(key, "")]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required config: {', '.join(missing)}")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    def mask(value: str, show: int = 6) -> str:
        if not value:
            return ""
        return value[:show] + "*" * min(max(len(value) - show, 0), 20)

    return {
        "jira_url": os.environ.get("JIRA_URL", ""),
        "jira_username": os.environ.get("JIRA_USERNAME", ""),
        "jira_project_key": os.environ.get("JIRA_PROJECT_KEY", ""),
        "jql_filter": os.environ.get("JIRA_JQL_FILTER", ""),
        "groq_model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "groq_api_key_masked": mask(os.environ.get("GROQ_API_KEY", "")),
        "github_target_repo": os.environ.get("GITHUB_TARGET_REPO", ""),
        "github_reference_repo": os.environ.get("GITHUB_REFERENCE_REPO", ""),
        "github_pat_masked": mask(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")),
        "target_app_url": os.environ.get("TARGET_APP_URL", ""),
        "configured": {
            "jira": bool(os.environ.get("JIRA_URL") and os.environ.get("JIRA_API_TOKEN")),
            "llm": bool(os.environ.get("GROQ_API_KEY")),
            "github": bool(os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")),
            "target_app": bool(os.environ.get("TARGET_APP_URL")),
        },
    }


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return _serialize_state()


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    global STATE
    STATE = _initial_state()
    return _serialize_state()


@app.post("/api/requirements/fetch")
def fetch_requirements(payload: FetchRequirementsRequest) -> dict[str, Any]:
    _require_config("GROQ_API_KEY", "JIRA_URL")
    try:
        _reset_settings()
        from agents.requirement_analyser import RequirementAnalyserAgent
        from integrations.jira_client import JiraClient

        client = JiraClient()
        ids = [item.strip() for item in payload.requirement_ids.split(",") if item.strip()]
        requirements = [client.fetch_single_requirement(req_id) for req_id in ids] if ids else client.fetch_requirements()
        STATE["raw_requirements"] = [req.model_dump() for req in requirements]
        _append_message(f"Fetched {len(requirements)} requirements")

        agent = RequirementAnalyserAgent()
        analyses = []
        for req in requirements:
            analysis = agent.analyze(req)
            analyses.append({"requirement": req.model_dump(), "analysis": analysis.model_dump()})

        STATE["analyzed_requirements"] = analyses
        STATE["workflow_step"] = 1
        STATE["rejected_step"] = -1
        _append_message(f"Analyzed {len(analyses)} requirements")
        return _serialize_state()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/demo/load")
def load_demo() -> dict[str, Any]:
    _require_config("GROQ_API_KEY")
    try:
        _reset_settings()
        from agents.requirement_analyser import RequirementAnalyserAgent
        from models.requirement import Requirement

        sample_req = {
            "id": "DEMO-001",
            "title": "User Login with Email and Password",
            "description": (
                "As a user, I want to log in using my email and password so I can access my dashboard. "
                "The system should validate credentials and redirect to the dashboard on success."
            ),
            "acceptance_criteria": (
                "1. User can enter email and password\n"
                "2. System validates credentials\n"
                "3. Shows error for invalid credentials\n"
                "4. Redirects to dashboard on success\n"
                "5. Session token is generated"
            ),
            "labels": ["authentication", "security"],
            "priority": "High",
            "status": "To Do",
            "issue_type": "Story",
            "source": "demo",
            "url": "",
        }

        req = Requirement(**sample_req)
        analysis = RequirementAnalyserAgent().analyze(req)
        STATE["raw_requirements"] = [sample_req]
        STATE["analyzed_requirements"] = [{"requirement": sample_req, "analysis": analysis.model_dump()}]
        STATE["workflow_step"] = 1
        STATE["rejected_step"] = -1
        _append_message("Demo: Analyzed sample requirement")
        return _serialize_state()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/requirements/approve")
def approve_requirements() -> dict[str, Any]:
    STATE["workflow_step"] = 2
    STATE["rejected_step"] = -1
    _append_message("Requirements APPROVED by human")
    return _serialize_state()


@app.post("/api/requirements/reject")
def reject_requirements() -> dict[str, Any]:
    STATE["rejected_step"] = 1
    _append_message("Requirements REJECTED by human")
    return _serialize_state()


@app.post("/api/requirements/regenerate")
def regenerate_requirements(payload: FeedbackRequest) -> dict[str, Any]:
    _require_config("GROQ_API_KEY")
    try:
        _reset_settings()
        from agents.requirement_analyser import RequirementAnalyserAgent
        from models.requirement import Requirement

        analyses = []
        agent = RequirementAnalyserAgent()
        for item in STATE["analyzed_requirements"]:
            req = Requirement(**item["requirement"])
            analysis = agent.analyze(req, feedback=payload.feedback)
            analyses.append({"requirement": item["requirement"], "analysis": analysis.model_dump()})

        STATE["analyzed_requirements"] = analyses
        _append_message(f"Regenerated analysis with feedback: {payload.feedback[:50]}")
        return _serialize_state()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/testcases/generate")
def generate_testcases(payload: FeedbackRequest | None = None) -> dict[str, Any]:
    _require_config("GROQ_API_KEY")
    try:
        _reset_settings()
        from agents.testcase_generator import TestCaseGeneratorAgent
        from models.requirement import Requirement, RequirementAnalysis

        feedback = payload.feedback if payload else ""
        agent = TestCaseGeneratorAgent()
        all_testcases = []
        for item in STATE["analyzed_requirements"]:
            req = Requirement(**item["requirement"])
            analysis = RequirementAnalysis(**item["analysis"])
            testcases = agent.generate(req, analysis, feedback=feedback)
            all_testcases.extend([testcase.model_dump() for testcase in testcases])

        STATE["generated_testcases"] = all_testcases
        _append_message("Regenerated test cases with feedback" if feedback else f"Generated {len(all_testcases)} test cases")
        return _serialize_state()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/testcases/approve")
def approve_testcases() -> dict[str, Any]:
    STATE["workflow_step"] = 3
    STATE["rejected_step"] = -1
    _append_message("Test cases APPROVED by human")
    return _serialize_state()


@app.post("/api/testcases/reject")
def reject_testcases() -> dict[str, Any]:
    STATE["rejected_step"] = 2
    _append_message("Test cases REJECTED by human")
    return _serialize_state()


@app.post("/api/scripts/generate")
def generate_scripts(payload: FeedbackRequest | None = None) -> dict[str, Any]:
    _require_config("GROQ_API_KEY")
    try:
        _reset_settings()
        from agents.script_generator import ScriptGeneratorAgent
        from models.testcase import TestCase

        feedback = payload.feedback if payload else ""
        agent = ScriptGeneratorAgent()
        test_cases = [TestCase(**testcase) for testcase in STATE["generated_testcases"]]
        repo_analysis = agent.analyze_repository()
        script = agent.generate(test_cases=test_cases, repo_analysis=repo_analysis, feedback=feedback)

        STATE["generated_scripts"] = [file.model_dump() for file in script.files]
        STATE["script_dependencies"] = script.dependencies
        STATE["script_setup_commands"] = script.setup_commands
        _append_message(f"Generated {len(script.files)} script files")
        return _serialize_state()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scripts/approve")
def approve_scripts() -> dict[str, Any]:
    STATE["workflow_step"] = 4
    STATE["rejected_step"] = -1
    _append_message("Scripts APPROVED by human")
    return _serialize_state()


@app.post("/api/scripts/reject")
def reject_scripts() -> dict[str, Any]:
    STATE["rejected_step"] = 3
    _append_message("Scripts REJECTED by human")
    return _serialize_state()


@app.post("/api/execution/run")
def run_execution() -> dict[str, Any]:
    try:
        _reset_settings()
        from agents.test_executor import TestExecutorAgent
        from models.script import GeneratedFile, TestScript

        files = [GeneratedFile(**file) for file in STATE["generated_scripts"]]
        script = TestScript(
            files=files,
            dependencies=STATE["script_dependencies"],
            setup_commands=STATE["script_setup_commands"],
        )
        result = TestExecutorAgent().execute(script)
        STATE["execution_results"] = [result.model_dump()]
        _append_message(f"Execution: {result.status}")
        return _serialize_state()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/commit-pr")
def commit_pr() -> dict[str, Any]:
    target_repo = os.environ.get("GITHUB_TARGET_REPO", "repo")
    STATE["pr_url"] = f"https://github.com/{target_repo}/pull/1"
    STATE["workflow_step"] = 5
    _append_message("PR created")
    return _serialize_state()
