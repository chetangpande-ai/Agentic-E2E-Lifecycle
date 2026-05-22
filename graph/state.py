"""
LangGraph state definition for the STLC workflow.
Unified state that flows through all four workflows.
"""

from typing import List, Dict, Optional, Any, Annotated
from pydantic import BaseModel, Field
import operator


class AgenticQEState(BaseModel):
    """
    Master state for the entire STLC agentic workflow.
    Flows through: Requirements → Test Cases → Scripts → Execution.
    """

    # === Source Configuration ===
    source_type: str = Field(default="jira", description="Requirement source")
    jql_filter: str = Field(default="", description="Custom JQL filter")
    requirement_ids: List[str] = Field(default_factory=list, description="Specific requirement IDs to process")

    # === Workflow 1: Requirement Analysis ===
    raw_requirements: List[Dict[str, Any]] = Field(default_factory=list, description="Raw requirements from Jira")
    analyzed_requirements: List[Dict[str, Any]] = Field(default_factory=list, description="Analyzed requirements")
    requirement_hitl_status: str = Field(default="pending", description="HITL decision: pending|approved|rejected|regenerate")
    requirement_feedback: str = Field(default="", description="HITL feedback text")

    # === Workflow 2: Test Case Generation ===
    generated_testcases: List[Dict[str, Any]] = Field(default_factory=list, description="Generated test cases")
    testcase_hitl_status: str = Field(default="pending", description="HITL decision")
    testcase_feedback: str = Field(default="", description="HITL feedback text")

    # === Workflow 3: Script Generation ===
    repo_analysis: Dict[str, Any] = Field(default_factory=dict, description="Repository analysis results")
    web_crawl_data: str = Field(default="", description="Playwright MCP crawl data")
    generated_scripts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated script files")
    script_dependencies: List[str] = Field(default_factory=list, description="NPM dependencies")
    script_setup_commands: List[str] = Field(default_factory=list, description="Setup commands")
    script_hitl_status: str = Field(default="pending", description="HITL decision")
    script_feedback: str = Field(default="", description="HITL feedback text")

    # === Workflow 4: Execution ===
    execution_results: List[Dict[str, Any]] = Field(default_factory=list, description="Test execution results")
    auto_heal_attempts: int = Field(default=0, description="Number of auto-heal attempts used")
    pr_url: str = Field(default="", description="GitHub PR URL")

    # === Control Flow ===
    current_workflow: str = Field(default="fetch_requirements", description="Current active workflow step")
    error: str = Field(default="", description="Error message if any")
    messages: List[str] = Field(default_factory=list, description="Workflow log messages")

    class Config:
        arbitrary_types_allowed = True
