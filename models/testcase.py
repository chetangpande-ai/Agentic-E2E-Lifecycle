"""
Test case data models.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum


class TestType(str, Enum):
    UI = "UI"
    API = "API"
    DB = "DB"
    KAFKA = "Kafka"
    MQ = "MQ"


class TestPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TestStep(BaseModel):
    """A single step within a test case."""

    step_number: int = Field(description="Step sequence number")
    action: str = Field(description="Action to perform")
    input_data: str = Field(default="", description="Input data for this step")
    expected_result: str = Field(description="Expected outcome of this step")


class TestCase(BaseModel):
    """A complete test case with all details."""

    id: str = Field(description="Unique test case ID (TC_XXX)")
    requirement_id: str = Field(default="", description="Reference to parent requirement")
    title: str = Field(description="Test case title")
    description: str = Field(default="", description="What is being tested")
    preconditions: List[str] = Field(default_factory=list, description="Setup requirements")
    test_type: TestType = Field(default=TestType.UI, description="Type of test")
    priority: TestPriority = Field(default=TestPriority.P2, description="Test priority")
    steps: List[TestStep] = Field(default_factory=list, description="Ordered test steps")
    test_data: Dict[str, str] = Field(default_factory=dict, description="Parameterized test data")
    expected_result: str = Field(default="", description="Overall expected outcome")
    tags: List[str] = Field(default_factory=list, description="Test tags/labels")
