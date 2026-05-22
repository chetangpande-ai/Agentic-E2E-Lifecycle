"""
Test script data models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class FileType(str, Enum):
    FEATURE = "feature"
    STEP_DEFINITION = "step_definition"
    PAGE_OBJECT = "page_object"
    CONFIG = "config"
    HELPER = "helper"
    FIXTURE = "fixture"


class GeneratedFile(BaseModel):
    """A single generated test file."""

    path: str = Field(description="Relative file path (e.g., features/login.feature)")
    content: str = Field(description="File content")
    file_type: FileType = Field(description="Type of file")


class TestScript(BaseModel):
    """Collection of generated test script files."""

    id: str = Field(default="", description="Script set identifier")
    testcase_ids: List[str] = Field(default_factory=list, description="Test cases covered")
    files: List[GeneratedFile] = Field(default_factory=list, description="Generated files")
    dependencies: List[str] = Field(default_factory=list, description="NPM packages required")
    setup_commands: List[str] = Field(default_factory=list, description="Setup commands to run")
    framework: str = Field(default="playwright-bdd", description="Test framework used")
    language: str = Field(default="typescript", description="Programming language")


class RepoAnalysis(BaseModel):
    """Analysis results of an existing test automation repository."""

    framework: str = Field(default="", description="Detected framework")
    test_pattern: str = Field(default="", description="Test pattern (BDD, TDD, POM)")
    language: str = Field(default="", description="Primary language")
    directory_structure: dict = Field(default_factory=dict)
    naming_conventions: dict = Field(default_factory=dict)
    reusable_components: List[str] = Field(default_factory=list)
    configuration_approach: str = Field(default="")
    key_patterns: List[str] = Field(default_factory=list)
    is_empty: bool = Field(default=True, description="Whether the repo is empty")
