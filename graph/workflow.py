"""
Main LangGraph workflow compilation.
Assembles all nodes and edges into the StateGraph.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import AgenticQEState
from graph.nodes import (
    fetch_requirements,
    analyze_requirements,
    hitl_requirement_review,
    generate_testcases,
    hitl_testcase_review,
    analyze_repository,
    generate_scripts,
    hitl_script_review,
    execute_tests,
    commit_and_pr,
    workflow_end,
)
from graph.edges import (
    route_after_requirement_hitl,
    route_after_testcase_hitl,
    route_after_script_hitl,
    route_test_type,
    route_execution_result,
)
from utils.logger import logger


def build_workflow():
    """
    Build and compile the complete STLC agentic workflow graph.
    
    Returns:
        Compiled LangGraph with checkpointing enabled.
    """
    logger.info("🏗️ Building STLC workflow graph...")

    # Create the state graph
    graph = StateGraph(AgenticQEState)

    # ============================================================
    # Add all nodes
    # ============================================================

    # Workflow 1: Requirement Analysis
    graph.add_node("fetch_requirements", fetch_requirements)
    graph.add_node("analyze_requirements", analyze_requirements)
    graph.add_node("hitl_requirement_review", hitl_requirement_review)

    # Workflow 2: Test Case Generation
    graph.add_node("generate_testcases", generate_testcases)
    graph.add_node("hitl_testcase_review", hitl_testcase_review)

    # Workflow 3: Script Generation
    graph.add_node("analyze_repository", analyze_repository)
    graph.add_node("generate_scripts", generate_scripts)
    graph.add_node("hitl_script_review", hitl_script_review)

    # Workflow 4: Test Execution
    graph.add_node("execute_tests", execute_tests)
    graph.add_node("commit_and_pr", commit_and_pr)

    # Terminal node
    graph.add_node("workflow_end", workflow_end)

    # ============================================================
    # Add edges
    # ============================================================

    # START → Fetch Requirements
    graph.add_edge(START, "fetch_requirements")

    # Workflow 1 flow
    graph.add_edge("fetch_requirements", "analyze_requirements")
    graph.add_edge("analyze_requirements", "hitl_requirement_review")
    graph.add_conditional_edges(
        "hitl_requirement_review",
        route_after_requirement_hitl,
        {
            "generate_testcases": "generate_testcases",
            "analyze_requirements": "analyze_requirements",  # Regenerate
            "workflow_end": "workflow_end",  # Rejected
        },
    )

    # Workflow 2 flow
    graph.add_edge("generate_testcases", "hitl_testcase_review")
    graph.add_conditional_edges(
        "hitl_testcase_review",
        route_after_testcase_hitl,
        {
            "analyze_repository": "analyze_repository",
            "generate_testcases": "generate_testcases",  # Regenerate
            "workflow_end": "workflow_end",  # Rejected
        },
    )

    # Workflow 3 flow
    graph.add_conditional_edges(
        "analyze_repository",
        route_test_type,
        {
            "generate_scripts": "generate_scripts",
        },
    )
    graph.add_edge("generate_scripts", "hitl_script_review")
    graph.add_conditional_edges(
        "hitl_script_review",
        route_after_script_hitl,
        {
            "execute_tests": "execute_tests",
            "generate_scripts": "generate_scripts",  # Regenerate
            "workflow_end": "workflow_end",  # Rejected
        },
    )

    # Workflow 4 flow
    graph.add_conditional_edges(
        "execute_tests",
        route_execution_result,
        {
            "commit_and_pr": "commit_and_pr",
            "hitl_script_review": "hitl_script_review",  # Failed → back to review
        },
    )
    graph.add_edge("commit_and_pr", "workflow_end")

    # Terminal
    graph.add_edge("workflow_end", END)

    # ============================================================
    # Compile with checkpointing
    # ============================================================

    # Use MemorySaver for development; switch to SqliteSaver/PostgresSaver for production
    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("✅ Workflow graph compiled successfully")
    return compiled


# Global workflow instance
_workflow = None


def get_workflow():
    """Get or create the singleton workflow instance."""
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow
