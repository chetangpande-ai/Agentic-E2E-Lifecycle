"""Connectivity checker utility for external integrations."""
import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger


class ConnectivityChecker:
    """Check connectivity to external services and integrations."""

    def __init__(self):
        """Initialize the connectivity checker."""
        self.results: Dict[str, Dict] = {}

    def check_groq_llm(self) -> Tuple[bool, str]:
        """Check Groq LLM connectivity and API key validity."""
        try:
            from langchain_groq import ChatGroq

            api_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"')
            if not api_key:
                return False, "GROQ_API_KEY not set"

            llm = ChatGroq(
                model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip().strip('"'),
                temperature=0.1,
                api_key=api_key,
                max_tokens=20,
            )
            resp = llm.invoke("hi")
            self.results["groq_llm"] = {"status": "OK", "model": os.environ.get("GROQ_MODEL")}
            return True, f"OK - Model: {os.environ.get('GROQ_MODEL')}"
        except TimeoutError:
            self.results["groq_llm"] = {"status": "TIMEOUT", "error": "Request timed out"}
            return False, "TIMEOUT - Groq API request timed out"
        except Exception as e:
            error_msg = str(e)[:200]
            self.results["groq_llm"] = {"status": "FAIL", "error": error_msg}
            return False, f"FAIL - {error_msg}"

    def check_jira(self) -> Tuple[bool, str]:
        """Check Jira connectivity and authentication."""
        try:
            from atlassian import Jira

            jira_url = os.environ.get("JIRA_URL", "").strip().strip('"')
            username = os.environ.get("JIRA_USERNAME", "").strip().strip('"')
            api_token = os.environ.get("JIRA_API_TOKEN", "").strip().strip('"')

            if not all([jira_url, username, api_token]):
                missing = []
                if not jira_url:
                    missing.append("JIRA_URL")
                if not username:
                    missing.append("JIRA_USERNAME")
                if not api_token:
                    missing.append("JIRA_API_TOKEN")
                return False, f"Missing credentials: {', '.join(missing)}"

            jira = Jira(url=jira_url, username=username, password=api_token, cloud=True)
            project_key = os.environ.get("JIRA_PROJECT_KEY", "").strip().strip('"')
            if project_key:
                result = jira.jql(f'project = "{project_key}"', limit=1)
                issues_count = len(result.get("issues", []))
                self.results["jira"] = {"status": "OK", "project": project_key, "issues": issues_count}
                return True, f"OK - Found {issues_count} issues in {project_key}"
            else:
                self.results["jira"] = {"status": "OK", "authenticated": True}
                return True, "OK - Authenticated (no project key set)"
        except TimeoutError:
            self.results["jira"] = {"status": "TIMEOUT", "error": "Request timed out"}
            return False, "TIMEOUT - Jira API request timed out"
        except Exception as e:
            error_msg = str(e)[:300]
            self.results["jira"] = {"status": "FAIL", "error": error_msg}
            return False, f"FAIL - {error_msg}"

    def check_github(self) -> Tuple[bool, str]:
        """Check GitHub connectivity and token validity."""
        try:
            import httpx

            token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "").strip().strip('"')
            if not token:
                return False, "GITHUB_PERSONAL_ACCESS_TOKEN not set"

            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            target_repo = os.environ.get("GITHUB_TARGET_REPO", "").strip().strip('"')
            ref_repo = os.environ.get("GITHUB_REFERENCE_REPO", "").strip().strip('"')

            results = {}
            if target_repo:
                try:
                    r = httpx.get(f"https://api.github.com/repos/{target_repo}", headers=headers, timeout=5.0)
                    results["target"] = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
                except httpx.TimeoutException:
                    results["target"] = "TIMEOUT"
                except Exception as e:
                    results["target"] = f"ERROR: {str(e)[:50]}"

            if ref_repo:
                try:
                    r = httpx.get(f"https://api.github.com/repos/{ref_repo}", headers=headers, timeout=5.0)
                    results["reference"] = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
                except httpx.TimeoutException:
                    results["reference"] = "TIMEOUT"
                except Exception as e:
                    results["reference"] = f"ERROR: {str(e)[:50]}"

            if results:
                self.results["github"] = {"status": "OK", "repos": results}
                return True, f"OK - {results}"
            else:
                self.results["github"] = {"status": "WARNING", "message": "No repos configured"}
                return True, "WARNING - No repos configured (set GITHUB_TARGET_REPO and/or GITHUB_REFERENCE_REPO)"
        except Exception as e:
            self.results["github"] = {"status": "FAIL", "error": str(e)[:200]}
            return False, f"FAIL - {str(e)[:200]}"

    def check_all(self) -> Dict[str, Tuple[bool, str]]:
        """Check all integrations and return results."""
        all_results = {}
        logger.info("Starting connectivity checks...")

        all_results["groq_llm"] = self.check_groq_llm()
        all_results["jira"] = self.check_jira()
        all_results["github"] = self.check_github()

        logger.info("Connectivity checks complete")
        return all_results

    def get_summary(self) -> Dict:
        """Get a summary of all connectivity check results."""
        return self.results


if __name__ == "__main__":
    checker = ConnectivityChecker()
    results = checker.check_all()

    print("\n" + "=" * 70)
    print("CONNECTIVITY CHECK SUMMARY")
    print("=" * 70)

    for service, (success, message) in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"\n{service.upper()}: {status}")
        print(f"  {message}")

    print("\n" + "=" * 70)
