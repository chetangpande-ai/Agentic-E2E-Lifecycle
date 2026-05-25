"""
GitHub commit and pull request helper.
Uses the GitHub REST API instead of local git push to avoid credential-manager
interference on Windows.
"""

import base64
import time
from typing import Dict, List
from urllib.parse import quote

import httpx

from config.settings import get_settings
from models.script import GeneratedFile


class GitHubPRClient:
    """Creates a branch, commits generated files, and opens a PR."""

    def __init__(self):
        self.settings = get_settings()
        if "/" not in self.settings.github_target_repo:
            raise ValueError("GITHUB_TARGET_REPO must be in owner/repo format")
        self.owner, self.repo = self.settings.github_target_repo.split("/", 1)

    def create_pr(
        self,
        files: List[GeneratedFile],
        branch_name: str,
        title: str,
        body: str,
        base_branch: str | None = None,
    ) -> Dict[str, str]:
        if not files:
            raise ValueError("No generated files available to commit")
        if not self.settings.github_personal_access_token:
            raise ValueError("Missing GitHub personal access token")

        base = base_branch or self.settings.github_target_branch or "main"
        branch = self._unique_branch(branch_name)

        self._ensure_base_branch(base)
        base_sha = self._get_branch_sha(base)
        self._create_branch(branch, base_sha)
        self._commit_files(files, branch)
        pr_url = self._create_pull_request(title, body, branch, base)

        repo_url = f"https://github.com/{self.settings.github_target_repo}"
        return {
            "repo": self.settings.github_target_repo,
            "branch": branch,
            "base_branch": base,
            "pr_url": pr_url,
            "compare_url": f"{repo_url}/compare/{base}...{branch}?expand=1",
        }

    def _ensure_base_branch(self, base_branch: str) -> None:
        branches = self._api("GET", "/branches").json()
        if any(branch.get("name") == base_branch for branch in branches):
            return
        if branches:
            available = ", ".join(sorted(branch.get("name", "") for branch in branches))
            raise RuntimeError(f"Target repository has branches ({available}) but no {base_branch} branch")

        self._api(
            "PUT",
            "/contents/README.md",
            json={
                "message": "Initialize repository",
                "content": base64.b64encode(f"# {self.repo}\n".encode("utf-8")).decode("ascii"),
                "branch": base_branch,
            },
            expected={200, 201},
        )

    def _get_branch_sha(self, branch: str) -> str:
        data = self._api("GET", f"/git/ref/heads/{quote(branch, safe='')}").json()
        return data["object"]["sha"]

    def _create_branch(self, branch: str, base_sha: str) -> None:
        self._api(
            "POST",
            "/git/refs",
            json={
                "ref": f"refs/heads/{branch}",
                "sha": base_sha,
            },
            expected={201},
        )

    def _commit_files(self, files: List[GeneratedFile], branch: str) -> None:
        for file in files:
            path = file.path.replace("\\", "/")
            payload = {
                "message": f"Add {file.path}",
                "content": base64.b64encode(file.content.encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            existing_sha = self._get_file_sha(path, branch)
            if existing_sha:
                payload["sha"] = existing_sha

            self._api(
                "PUT",
                f"/contents/{quote(path, safe='/')}",
                json=payload,
                expected={200, 201},
            )

    def _get_file_sha(self, path: str, branch: str) -> str:
        response = self._api(
            "GET",
            f"/contents/{quote(path, safe='/')}?ref={quote(branch, safe='')}",
            expected={200, 404},
        )
        if response.status_code == 404:
            return ""
        data = response.json()
        return data.get("sha", "")

    def _create_pull_request(self, title: str, body: str, head: str, base: str) -> str:
        response = self._api(
            "POST",
            "/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
            expected={201, 422},
        )
        if response.status_code == 201:
            return response.json()["html_url"]

        existing = self._find_existing_pull_request(head, base)
        if existing:
            return existing
        raise RuntimeError(f"GitHub PR creation failed (422): {response.text}")

    def _find_existing_pull_request(self, head: str, base: str) -> str:
        encoded_head = quote(f"{self.owner}:{head}", safe="")
        encoded_base = quote(base, safe="")
        response = self._api(
            "GET",
            f"/pulls?state=open&head={encoded_head}&base={encoded_base}",
            expected={200},
        )
        pulls = response.json()
        return pulls[0]["html_url"] if pulls else ""

    def _api(
        self,
        method: str,
        path: str,
        json: Dict | None = None,
        expected: set[int] | None = None,
    ) -> httpx.Response:
        expected = expected or {200}
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}{path}"
        response = httpx.request(
            method,
            url,
            headers={
                "Authorization": f"Bearer {self.settings.github_personal_access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=json,
            timeout=60,
        )
        if response.status_code not in expected:
            detail = self._sanitize(response.text)
            if response.status_code == 403 and "Resource not accessible by personal access token" in detail:
                raise RuntimeError(
                    "GitHub token cannot write repository contents. Update the PAT for "
                    f"{self.settings.github_target_repo} with repository permissions: "
                    "Contents = Read and write, Pull requests = Read and write."
                )
            raise RuntimeError(
                f"GitHub API request failed ({method} {path}, {response.status_code}): "
                f"{detail}"
            )
        return response

    @staticmethod
    def _unique_branch(branch_name: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in "-_/" else "-" for ch in branch_name).strip("-/")
        safe = safe or "auto-tests"
        return f"{safe}-{int(time.time())}"

    @staticmethod
    def _sanitize(message: str) -> str:
        token = get_settings().github_personal_access_token
        return message.replace(token, "***") if token else message
