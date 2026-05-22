"""
Test execution result data models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class ExecutionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIP = "SKIP"


class TestResult(BaseModel):
    """Result of a single test execution."""

    test_name: str = Field(description="Test case/scenario name")
    status: ExecutionStatus = Field(description="Pass/Fail/Error/Skip")
    duration: str = Field(default="0ms", description="Execution duration")
    error_message: str = Field(default="", description="Error message if failed")
    stack_trace: str = Field(default="", description="Full stack trace if failed")


class AutoHealAttempt(BaseModel):
    """Record of an auto-heal attempt."""

    attempt_number: int = Field(description="Attempt number (1-3)")
    root_cause: str = Field(description="Identified root cause")
    fix_description: str = Field(description="What was fixed")
    success: bool = Field(description="Whether the fix resolved the issue")


class ExecutionResult(BaseModel):
    """Complete test execution result."""

    id: str = Field(default="", description="Execution ID")
    script_id: str = Field(default="", description="Reference to test script")
    status: ExecutionStatus = Field(default=ExecutionStatus.ERROR)
    total_tests: int = Field(default=0)
    passed: int = Field(default=0)
    failed: int = Field(default=0)
    skipped: int = Field(default=0)
    execution_time: str = Field(default="")
    results: List[TestResult] = Field(default_factory=list)
    auto_heal_attempts: List[AutoHealAttempt] = Field(default_factory=list)
    logs: str = Field(default="", description="Execution logs")
    pr_url: str = Field(default="", description="GitHub PR URL if created")
    executed_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Execution timestamp",
    )
