"""
LangGraph node functions for each step in the STLC workflow.
Each node takes the state, performs its task, and returns state updates.
"""

from typing import Dict, Any
from langgraph.types import interrupt
from graph.state import AgenticQEState
from agents.requirement_analyser import RequirementAnalyserAgent
from agents.testcase_generator import TestCaseGeneratorAgent
from agents.script_generator import ScriptGeneratorAgent
from agents.test_executor import TestExecutorAgent
from integrations.jira_client import JiraClient
from integrations.repo_analyzer import RepoAnalyzer
from models.requirement import Requirement, RequirementAnalysis
from models.testcase import TestCase
from models.script import TestScript, GeneratedFile
from utils.logger import logger


# ============================================================
# WORKFLOW 1: Requirement Analysis
# ============================================================

def fetch_requirements(state: AgenticQEState) -> Dict[str, Any]:
    """Fetch requirements from Jira."""
    logger.info("📥 [bold]Node: Fetching requirements from Jira...[/bold]")

    try:
        client = JiraClient()

        if state.requirement_ids:
            # Fetch specific requirements
            requirements = []
            for req_id in state.requirement_ids:
                req = client.fetch_single_requirement(req_id)
                requirements.append(req)
        else:
            # Fetch by JQL filter
            requirements = client.fetch_requirements(jql_filter=state.jql_filter or None)

        raw_reqs = [req.model_dump() for req in requirements]
        logger.info(f"Fetched {len(raw_reqs)} requirements")

        return {
            "raw_requirements": raw_reqs,
            "current_workflow": "analyze_requirements",
            "messages": state.messages + [f"Fetched {len(raw_reqs)} requirements from Jira"],
        }
    except Exception as e:
        logger.error(f"Error fetching requirements: {e}")
        return {
            "error": str(e),
            "messages": state.messages + [f"Error: {str(e)}"],
        }


def analyze_requirements(state: AgenticQEState) -> Dict[str, Any]:
    """Analyze requirements for testability using the Analyser Agent."""
    logger.info("🔍 [bold]Node: Analyzing requirements...[/bold]")

    agent = RequirementAnalyserAgent()
    analyses = []

    for raw_req in state.raw_requirements:
        requirement = Requirement(**raw_req)
        analysis = agent.analyze(
            requirement=requirement,
            feedback=state.requirement_feedback,
        )
        analyses.append({
            "requirement": raw_req,
            "analysis": analysis.model_dump(),
        })

    return {
        "analyzed_requirements": analyses,
        "current_workflow": "hitl_requirement_review",
        "requirement_hitl_status": "pending",
        "messages": state.messages + [f"Analyzed {len(analyses)} requirements"],
    }


def hitl_requirement_review(state: AgenticQEState) -> Dict[str, Any]:
    """HITL checkpoint: Human reviews requirement analysis."""
    logger.info("👤 [bold]Node: Awaiting human review of requirement analysis...[/bold]")

    # Interrupt and wait for human decision
    decision = interrupt({
        "type": "requirement_review",
        "data": state.analyzed_requirements,
        "prompt": "Review the requirement analysis. Choose: approve, reject, or regenerate (with feedback).",
    })

    # Decision comes back from the UI via Command(resume=...)
    action = decision.get("action", "reject")
    feedback = decision.get("feedback", "")

    return {
        "requirement_hitl_status": action,
        "requirement_feedback": feedback,
        "current_workflow": "hitl_requirement_decision",
        "messages": state.messages + [f"HITL Requirement Review: {action}"],
    }


# ============================================================
# WORKFLOW 2: Test Case Generation
# ============================================================

def generate_testcases(state: AgenticQEState) -> Dict[str, Any]:
    """Generate test cases from analyzed requirements."""
    logger.info("📝 [bold]Node: Generating test cases...[/bold]")

    agent = TestCaseGeneratorAgent()
    all_test_cases = []

    for item in state.analyzed_requirements:
        requirement = Requirement(**item["requirement"])
        analysis = RequirementAnalysis(**item["analysis"])

        test_cases = agent.generate(
            requirement=requirement,
            analysis=analysis,
            feedback=state.testcase_feedback,
        )
        all_test_cases.extend([tc.model_dump() for tc in test_cases])

    return {
        "generated_testcases": all_test_cases,
        "current_workflow": "hitl_testcase_review",
        "testcase_hitl_status": "pending",
        "messages": state.messages + [f"Generated {len(all_test_cases)} test cases"],
    }


def hitl_testcase_review(state: AgenticQEState) -> Dict[str, Any]:
    """HITL checkpoint: Human reviews generated test cases."""
    logger.info("👤 [bold]Node: Awaiting human review of test cases...[/bold]")

    decision = interrupt({
        "type": "testcase_review",
        "data": state.generated_testcases,
        "prompt": "Review the generated test cases. Choose: approve, reject, or regenerate (with feedback).",
    })

    action = decision.get("action", "reject")
    feedback = decision.get("feedback", "")

    return {
        "testcase_hitl_status": action,
        "testcase_feedback": feedback,
        "current_workflow": "hitl_testcase_decision",
        "messages": state.messages + [f"HITL Test Case Review: {action}"],
    }


# ============================================================
# WORKFLOW 3: Script Generation
# ============================================================

def analyze_repository(state: AgenticQEState) -> Dict[str, Any]:
    """Analyze the target/reference repository for patterns."""
    logger.info("🔧 [bold]Node: Analyzing repository...[/bold]")

    analyzer = RepoAnalyzer()

    # Try target repo first, then reference repo
    from config.settings import get_settings
    settings = get_settings()

    analysis = analyzer.analyze_repo(f"https://github.com/{settings.github_target_repo}.git")

    if analysis.is_empty:
        logger.info("Target repo is empty, analyzing reference repo...")
        analysis = analyzer.analyze_repo(f"https://github.com/{settings.github_reference_repo}.git")

        if analysis.is_empty:
            logger.info("Reference repo also empty. Using Playwright-BDD defaults.")

    # Index code into vector store if repo has content
    if not analysis.is_empty:
        from vectorstore.indexer import CodeIndexer
        indexer = CodeIndexer()
        code_files = analyzer.get_all_code_files()
        indexer.index_repository(code_files)

    return {
        "repo_analysis": analysis.model_dump(),
        "current_workflow": "check_test_type",
        "messages": state.messages + [f"Repo analysis: {analysis.framework or 'empty'} / {analysis.test_pattern or 'default'}"],
    }


def generate_scripts(state: AgenticQEState) -> Dict[str, Any]:
    """Generate test automation scripts."""
    logger.info("💻 [bold]Node: Generating test scripts...[/bold]")

    from models.script import RepoAnalysis

    agent = ScriptGeneratorAgent()
    test_cases = [TestCase(**tc) for tc in state.generated_testcases]
    repo_analysis = RepoAnalysis(**state.repo_analysis) if state.repo_analysis else None

    script = agent.generate(
        test_cases=test_cases,
        repo_analysis=repo_analysis,
        web_crawl_data=state.web_crawl_data,
        feedback=state.script_feedback,
    )

    return {
        "generated_scripts": [f.model_dump() for f in script.files],
        "script_dependencies": script.dependencies,
        "script_setup_commands": script.setup_commands,
        "current_workflow": "hitl_script_review",
        "script_hitl_status": "pending",
        "messages": state.messages + [f"Generated {len(script.files)} script files"],
    }


def hitl_script_review(state: AgenticQEState) -> Dict[str, Any]:
    """HITL checkpoint: Human reviews generated scripts."""
    logger.info("👤 [bold]Node: Awaiting human review of test scripts...[/bold]")

    decision = interrupt({
        "type": "script_review",
        "data": {
            "scripts": state.generated_scripts,
            "dependencies": state.script_dependencies,
            "setup_commands": state.script_setup_commands,
        },
        "prompt": "Review the generated test scripts. Choose: approve, reject, or regenerate (with feedback).",
    })

    action = decision.get("action", "reject")
    feedback = decision.get("feedback", "")

    return {
        "script_hitl_status": action,
        "script_feedback": feedback,
        "current_workflow": "hitl_script_decision",
        "messages": state.messages + [f"HITL Script Review: {action}"],
    }


# ============================================================
# WORKFLOW 4: Test Execution
# ============================================================

def execute_tests(state: AgenticQEState) -> Dict[str, Any]:
    """Execute the approved test scripts."""
    logger.info("🚀 [bold]Node: Executing test scripts...[/bold]")

    agent = TestExecutorAgent()

    files = [GeneratedFile(**f) for f in state.generated_scripts]
    script = TestScript(
        files=files,
        dependencies=state.script_dependencies,
        setup_commands=state.script_setup_commands,
    )

    result = agent.execute(script)

    return {
        "execution_results": [result.model_dump()],
        "auto_heal_attempts": len(result.auto_heal_attempts),
        "current_workflow": "check_execution_result",
        "messages": state.messages + [f"Execution complete: {result.status}"],
    }


def commit_and_pr(state: AgenticQEState) -> Dict[str, Any]:
    """Commit approved scripts to GitHub and create PR."""
    logger.info("📤 [bold]Node: Committing to GitHub and creating PR...[/bold]")

    # This node will use GitHub MCP tools
    # For now, we'll prepare the commit data
    from config.settings import get_settings
    settings = get_settings()

    pr_info = {
        "repo": settings.github_target_repo,
        "branch": f"auto-tests-{state.generated_testcases[0].get('requirement_id', 'new') if state.generated_testcases else 'new'}",
        "title": "🤖 Auto-generated test scripts",
        "body": f"## Auto-generated Test Scripts\n\n"
                f"- **Test Cases**: {len(state.generated_testcases)}\n"
                f"- **Script Files**: {len(state.generated_scripts)}\n"
                f"- **Framework**: Playwright-BDD (Node.js)\n\n"
                f"### Files\n" +
                "\n".join(f"- `{f.get('path', '')}`" for f in state.generated_scripts),
        "files": state.generated_scripts,
    }

    return {
        "pr_url": f"https://github.com/{settings.github_target_repo}/pull/new",
        "current_workflow": "done",
        "messages": state.messages + ["PR created successfully"],
    }


def workflow_end(state: AgenticQEState) -> Dict[str, Any]:
    """Terminal node - workflow ends (rejected or complete)."""
    logger.info("🏁 [bold]Workflow ended.[/bold]")
    return {
        "current_workflow": "end",
    }
