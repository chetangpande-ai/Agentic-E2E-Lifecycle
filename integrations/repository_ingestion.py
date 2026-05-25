"""
Main-branch repository ingestion and cached coding-agent analysis.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict

from agents.repository_analysis_agent import RepositoryAnalysisAgent
from config.settings import get_settings
from integrations.repo_analyzer import RepoAnalyzer
from models.script import RepoAnalysis
from utils.logger import logger
from vectorstore.indexer import CodeIndexer
from vectorstore.store import reset_collection


class RepositoryIngestionService:
    """Caches repo analysis by repo, branch, and latest main commit SHA."""

    COLLECTION_NAME = "code_patterns"

    def __init__(self):
        self.settings = get_settings()
        self.branch = self.settings.github_target_branch or "main"
        self.cache_path = Path(self.settings.chroma_persist_dir) / "repo_profiles.json"

    def analyze_target_then_reference(self) -> RepoAnalysis:
        target = self.analyze_repo(self.settings.github_target_repo)
        if not target.is_empty:
            return target

        logger.info("Target repo is empty, analyzing reference repo main...")
        reference = self.analyze_repo(self.settings.github_reference_repo)
        if reference.is_empty:
            logger.info("Reference repo also empty. Using Playwright-BDD defaults.")
        return reference

    def analyze_repo(self, repo: str) -> RepoAnalysis:
        repo_url = f"https://github.com/{repo}.git" if "/" in repo and not repo.startswith("http") else repo
        sha = self._remote_branch_sha(repo_url)
        if not sha:
            logger.info(f"Repository has no {self.branch} branch or is empty: {repo_url}")
            return RepoAnalysis(is_empty=True)

        cache = self._load_cache()
        key = self._cache_key(repo_url, self.branch, sha)
        if key in cache:
            logger.info(f"Using cached repository analysis for {repo_url}@{self.branch}:{sha[:8]}")
            return RepoAnalysis(**cache[key]["analysis"])

        logger.info(f"Refreshing repository ingestion for {repo_url}@{self.branch}:{sha[:8]}")
        analyzer = RepoAnalyzer()
        analysis = analyzer.analyze_repo(repo_url, branch=self.branch)
        if analysis.is_empty:
            return analysis

        code_files = analyzer.get_all_code_files()
        if code_files:
            reset_collection(self.COLLECTION_NAME)
            CodeIndexer().index_repository(code_files)
            analysis = RepositoryAnalysisAgent().analyze(
                code_files=code_files,
                heuristic_analysis=analysis,
            )

        cache[key] = {
            "repo_url": repo_url,
            "branch": self.branch,
            "sha": sha,
            "analysis": analysis.model_dump(),
        }
        self._save_cache(cache)
        return analysis

    def _remote_branch_sha(self, repo_url: str) -> str:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url, self.branch],
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        if result.returncode != 0:
            logger.warning(f"Could not inspect {self.branch} for {repo_url}: {result.stderr.strip()}")
            return ""

        parts = result.stdout.split()
        return parts[0] if len(parts) >= 2 else ""

    def _load_cache(self) -> Dict:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"Ignoring invalid repo profile cache: {self.cache_path}")
            return {}

    def _save_cache(self, cache: Dict) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    @staticmethod
    def _cache_key(repo_url: str, branch: str, sha: str) -> str:
        return f"{repo_url}|{branch}|{sha}"
