"""
Requirement data models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TestabilityScore(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Requirement(BaseModel):
    """Represents a requirement/user story from Jira."""

    id: str = Field(description="Jira issue key (e.g., PROJ-123)")
    title: str = Field(description="Issue summary/title")
    description: str = Field(default="", description="Full description")
    acceptance_criteria: str = Field(default="", description="Acceptance criteria text")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    priority: str = Field(default="Medium", description="Issue priority")
    status: str = Field(default="To Do", description="Issue status")
    issue_type: str = Field(default="Story", description="Issue type")
    source: str = Field(default="jira", description="Source system (jira/ado)")
    url: str = Field(default="", description="Link to the original issue")


class RequirementAnalysis(BaseModel):
    """Analysis output from the Requirement Analyser Agent."""

    requirement_id: str = Field(description="Reference to the source requirement")
    testability_score: TestabilityScore = Field(description="Testability rating")
    testability_justification: str = Field(default="", description="Why this score")
    clarity_assessment: str = Field(default="", description="Assessment of requirement clarity")
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    acceptance_criteria_gaps: List[str] = Field(default_factory=list)
    recommended_test_types: List[str] = Field(default_factory=list)
    risks_and_dependencies: List[str] = Field(default_factory=list)
    suggested_clarifications: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    estimated_test_cases_count: int = Field(default=0)
    summary: str = Field(default="", description="Analysis summary")
