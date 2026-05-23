"""
Jira REST API client for fetching requirements/user stories.
Uses atlassian-python-api library.
"""

from typing import List, Optional
from atlassian import Jira
from models.requirement import Requirement
from config.settings import get_settings
from utils.logger import logger, log_execution_start, log_execution_end, log_error, log_debug_data
import time


class JiraClient:
    """Client for interacting with Jira to fetch requirements."""

    def __init__(self):
        settings = get_settings()
        log_execution_start(logger, "JiraClient.__init__", {"url": settings.jira_url, "project": settings.jira_project_key})
        self.jira = Jira(
            url=settings.jira_url,
            username=settings.jira_username,
            password=settings.jira_api_token,
            cloud=True,
        )
        self.project_key = settings.jira_project_key
        self.default_jql = settings.jira_jql_filter
        logger.info(f"JiraClient initialized for project {self.project_key}")

    def fetch_requirements(
        self,
        jql_filter: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Requirement]:
        """
        Fetch requirements from Jira using JQL.
        
        Args:
            jql_filter: Custom JQL query. Uses default from config if not provided.
            max_results: Maximum number of results to return.
            
        Returns:
            List of Requirement objects.
        """
        jql = jql_filter or f'project = "{self.project_key}" AND {self.default_jql}'
        logger.info(f"[bold blue]Fetching requirements from Jira[/bold blue] | JQL: {jql}")

        try:
            response = self.jira.jql(jql, limit=max_results)
            issues = response.get("issues", [])
            logger.info(f"Found {len(issues)} requirements")

            requirements = []
            for issue in issues:
                fields = issue.get("fields", {})
                req = Requirement(
                    id=issue["key"],
                    title=fields.get("summary", ""),
                    description=fields.get("description", "") or "",
                    acceptance_criteria=self._extract_acceptance_criteria(fields),
                    labels=fields.get("labels", []),
                    priority=self._get_priority(fields),
                    status=self._get_status(fields),
                    issue_type=self._get_issue_type(fields),
                    source="jira",
                    url=f"{get_settings().jira_url}/browse/{issue['key']}",
                )
                requirements.append(req)

            return requirements

        except Exception as e:
            logger.error(f"Failed to fetch requirements from Jira: {e}")
            raise

    def fetch_single_requirement(self, issue_key: str) -> Requirement:
        """Fetch a single requirement by its Jira key."""
        logger.info(f"Fetching requirement: {issue_key}")
        try:
            issue = self.jira.issue(issue_key)
            fields = issue.get("fields", {})
            return Requirement(
                id=issue["key"],
                title=fields.get("summary", ""),
                description=fields.get("description", "") or "",
                acceptance_criteria=self._extract_acceptance_criteria(fields),
                labels=fields.get("labels", []),
                priority=self._get_priority(fields),
                status=self._get_status(fields),
                issue_type=self._get_issue_type(fields),
                source="jira",
                url=f"{get_settings().jira_url}/browse/{issue['key']}",
            )
        except Exception as e:
            logger.error(f"Failed to fetch requirement {issue_key}: {e}")
            raise

    def _extract_acceptance_criteria(self, fields: dict) -> str:
        """Extract acceptance criteria from various possible field locations."""
        # Check common custom field names for acceptance criteria
        ac = fields.get("customfield_10020", "")  # Common AC field
        if not ac:
            # Try to extract from description if AC section exists
            desc = fields.get("description", "") or ""
            if "acceptance criteria" in desc.lower():
                parts = desc.lower().split("acceptance criteria")
                if len(parts) > 1:
                    ac = parts[1].strip()
        return ac or ""

    def _get_priority(self, fields: dict) -> str:
        """Extract priority name from fields."""
        priority = fields.get("priority")
        if priority and isinstance(priority, dict):
            return priority.get("name", "Medium")
        return "Medium"

    def _get_status(self, fields: dict) -> str:
        """Extract status name from fields."""
        status = fields.get("status")
        if status and isinstance(status, dict):
            return status.get("name", "To Do")
        return "To Do"

    def _get_issue_type(self, fields: dict) -> str:
        """Extract issue type name from fields."""
        issue_type = fields.get("issuetype")
        if issue_type and isinstance(issue_type, dict):
            return issue_type.get("name", "Story")
        return "Story"
