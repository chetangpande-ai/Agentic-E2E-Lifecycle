"""
Central configuration using Pydantic Settings.
Loads all environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # --- LLM Configuration (Groq) ---
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Groq model name")
    groq_temperature: float = Field(default=0.1, description="LLM temperature")

    # --- Jira Configuration ---
    jira_url: str = Field(default="", description="Jira instance URL")
    jira_username: str = Field(default="", description="Jira username/email")
    jira_api_token: str = Field(default="", description="Jira API token")
    jira_project_key: str = Field(default="", description="Jira project key")
    jira_jql_filter: str = Field(
        default='issuetype = Story AND status = "To Do"',
        description="JQL filter for fetching requirements",
    )

    # --- GitHub Configuration ---
    github_personal_access_token: str = Field(default="", description="GitHub PAT")
    github_target_repo: str = Field(
        default="chetangpande-ai/HdfcBank-Test-Automation",
        description="Target repo for committing test scripts",
    )
    github_reference_repo: str = Field(
        default="chetangpande-ai/PW-Automation-Framework",
        description="Reference repo for Playwright-BDD patterns",
    )
    github_target_branch: str = Field(default="main", description="Target branch")

    # --- Target Application ---
    target_app_url: str = Field(default="", description="Target application URL for web crawling")

    # --- Vector Store ---
    chroma_persist_dir: str = Field(default="./chroma_db", description="ChromaDB persistence directory")
    embedding_model: str = Field(
        default="sentence-transformers/all-mpnet-base-v2",
        description="HuggingFace embedding model name",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
