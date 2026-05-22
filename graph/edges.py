"""
Conditional edge routing functions for the LangGraph workflow.
Controls HITL approve/reject/regenerate flow.
"""

from graph.state import AgenticQEState
from utils.logger import logger


def route_after_requirement_hitl(state: AgenticQEState) -> str:
    """Route after requirement HITL review."""
    status = state.requirement_hitl_status
    logger.info(f"Routing after requirement HITL: {status}")

    if status == "approved":
        return "generate_testcases"
    elif status == "regenerate":
        return "analyze_requirements"
    else:  # rejected
        return "workflow_end"


def route_after_testcase_hitl(state: AgenticQEState) -> str:
    """Route after test case HITL review."""
    status = state.testcase_hitl_status
    logger.info(f"Routing after testcase HITL: {status}")

    if status == "approved":
        return "analyze_repository"
    elif status == "regenerate":
        return "generate_testcases"
    else:
        return "workflow_end"


def route_after_script_hitl(state: AgenticQEState) -> str:
    """Route after script HITL review."""
    status = state.script_hitl_status
    logger.info(f"Routing after script HITL: {status}")

    if status == "approved":
        return "execute_tests"
    elif status == "regenerate":
        return "generate_scripts"
    else:
        return "workflow_end"


def route_test_type(state: AgenticQEState) -> str:
    """
    Route based on test type (UI vs non-UI).
    Web UI tests go through Playwright MCP crawling.
    """
    test_types = set()
    for tc in state.generated_testcases:
        test_types.add(tc.get("test_type", "UI"))

    if "UI" in test_types:
        logger.info("Web UI tests detected → Playwright MCP crawl path")
        return "generate_scripts"  # Web crawl integrated into script generation
    else:
        logger.info("Non-UI tests → Direct script generation")
        return "generate_scripts"


def route_execution_result(state: AgenticQEState) -> str:
    """Route based on test execution result."""
    if not state.execution_results:
        return "workflow_end"

    latest = state.execution_results[-1]
    status = latest.get("status", "ERROR")

    if status == "PASS":
        logger.info("Tests passed → Commit and PR")
        return "commit_and_pr"
    else:
        logger.info("Tests failed → Back to script review (HITL)")
        return "hitl_script_review"
