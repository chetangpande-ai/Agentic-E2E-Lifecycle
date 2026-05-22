"""
Repository analyzer for detecting patterns, frameworks, and reusable code.
Scans target/reference repositories to inform the script generator agent.
"""

import os
import tempfile
from typing import Dict, List, Optional
from pathlib import Path
import git
from models.script import RepoAnalysis
from config.settings import get_settings
from utils.logger import logger


class RepoAnalyzer:
    """Analyzes test automation repositories for patterns and reusable code."""

    # Known framework indicators
    FRAMEWORK_INDICATORS = {
        "playwright": ["playwright.config", "@playwright/test", "playwright"],
        "playwright-bdd": ["playwright-bdd", ".feature", "defineStep"],
        "selenium": ["selenium-webdriver", "webdriver"],
        "cypress": ["cypress.config", "cy."],
        "pytest": ["pytest", "conftest.py", "test_"],
        "jest": ["jest.config", "describe(", "it("],
        "testng": ["testng.xml", "@Test", "TestNG"],
    }

    def __init__(self, repo_url: Optional[str] = None):
        self.repo_url = repo_url
        self.repo_path = None
        self.settings = get_settings()

    def analyze_repo(self, repo_url: Optional[str] = None) -> RepoAnalysis:
        """
        Clone and analyze a repository for test automation patterns.
        
        Args:
            repo_url: GitHub repo URL. Uses target repo from config if not provided.
            
        Returns:
            RepoAnalysis object with detected patterns.
        """
        url = repo_url or f"https://github.com/{self.settings.github_target_repo}.git"
        logger.info(f"[bold yellow]Analyzing repository:[/bold yellow] {url}")

        try:
            # Clone to temp directory
            self.repo_path = tempfile.mkdtemp(prefix="repo_analysis_")
            repo = git.Repo.clone_from(url, self.repo_path)
            
            return self._perform_analysis()
        except git.exc.GitCommandError as e:
            if "empty" in str(e).lower() or "not found" in str(e).lower():
                logger.warning(f"Repository appears to be empty: {url}")
                return RepoAnalysis(is_empty=True)
            logger.error(f"Git error analyzing repo: {e}")
            return RepoAnalysis(is_empty=True)
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            return RepoAnalysis(is_empty=True)

    def analyze_local_path(self, path: str) -> RepoAnalysis:
        """Analyze a local repository path."""
        self.repo_path = path
        return self._perform_analysis()

    def _perform_analysis(self) -> RepoAnalysis:
        """Perform the actual repository analysis."""
        if not self.repo_path or not os.path.exists(self.repo_path):
            return RepoAnalysis(is_empty=True)

        files = self._get_file_tree()
        if not files:
            return RepoAnalysis(is_empty=True)

        framework = self._detect_framework(files)
        language = self._detect_language(files)
        test_pattern = self._detect_test_pattern(files)
        reusable = self._find_reusable_components(files)
        config_approach = self._detect_config_approach(files)
        structure = self._map_directory_structure(files)

        analysis = RepoAnalysis(
            framework=framework,
            test_pattern=test_pattern,
            language=language,
            directory_structure=structure,
            naming_conventions=self._detect_naming_conventions(files),
            reusable_components=reusable,
            configuration_approach=config_approach,
            key_patterns=self._extract_key_patterns(files),
            is_empty=False,
        )

        logger.info(f"Repo analysis complete: {framework} / {language} / {test_pattern}")
        return analysis

    def _get_file_tree(self) -> List[str]:
        """Get list of all files in the repository."""
        files = []
        for root, dirs, filenames in os.walk(self.repo_path):
            # Skip hidden and dependency directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(root, filename), self.repo_path)
                files.append(rel_path)
        return files

    def _detect_framework(self, files: List[str]) -> str:
        """Detect the test automation framework."""
        file_contents = self._read_key_files(files)
        all_text = " ".join(file_contents.values()) + " ".join(files)

        for framework, indicators in self.FRAMEWORK_INDICATORS.items():
            matches = sum(1 for ind in indicators if ind.lower() in all_text.lower())
            if matches >= 2:
                return framework

        return "unknown"

    def _detect_language(self, files: List[str]) -> str:
        """Detect the primary programming language."""
        ext_counts = {}
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in ['.ts', '.tsx']:
                ext_counts['typescript'] = ext_counts.get('typescript', 0) + 1
            elif ext in ['.js', '.jsx']:
                ext_counts['javascript'] = ext_counts.get('javascript', 0) + 1
            elif ext == '.py':
                ext_counts['python'] = ext_counts.get('python', 0) + 1
            elif ext == '.java':
                ext_counts['java'] = ext_counts.get('java', 0) + 1

        return max(ext_counts, key=ext_counts.get) if ext_counts else "typescript"

    def _detect_test_pattern(self, files: List[str]) -> str:
        """Detect the test design pattern."""
        has_features = any('.feature' in f for f in files)
        has_page_objects = any('page' in f.lower() and ('object' in f.lower() or 'model' in f.lower()) for f in files)
        has_pages = any('pages/' in f.lower() or 'page/' in f.lower() for f in files)

        patterns = []
        if has_features:
            patterns.append("BDD")
        if has_page_objects or has_pages:
            patterns.append("POM")
        
        return " + ".join(patterns) if patterns else "Standard"

    def _find_reusable_components(self, files: List[str]) -> List[str]:
        """Find reusable components in the codebase."""
        reusable = []
        keywords = ['util', 'helper', 'common', 'shared', 'fixture', 'hook', 'support', 'lib']
        for f in files:
            if any(k in f.lower() for k in keywords):
                reusable.append(f)
        return reusable

    def _detect_config_approach(self, files: List[str]) -> str:
        """Detect configuration approach."""
        configs = [f for f in files if 'config' in f.lower() or f.endswith('.env')]
        return ", ".join(configs[:5]) if configs else "None detected"

    def _map_directory_structure(self, files: List[str]) -> Dict:
        """Map the top-level directory structure."""
        dirs = set()
        for f in files:
            parts = Path(f).parts
            if len(parts) > 1:
                dirs.add(parts[0])
        return {"top_level_dirs": sorted(dirs)}

    def _detect_naming_conventions(self, files: List[str]) -> Dict:
        """Detect naming conventions."""
        return {
            "file_style": "kebab-case" if any('-' in Path(f).stem for f in files) else "camelCase",
            "test_prefix": "test_" if any(Path(f).name.startswith("test_") for f in files) else "",
        }

    def _extract_key_patterns(self, files: List[str]) -> List[str]:
        """Extract key patterns from the codebase."""
        patterns = []
        if any('fixture' in f.lower() for f in files):
            patterns.append("Uses fixtures for test setup")
        if any('hook' in f.lower() for f in files):
            patterns.append("Uses hooks for lifecycle management")
        if any('.feature' in f for f in files):
            patterns.append("BDD with Gherkin feature files")
        if any('step' in f.lower() and ('def' in f.lower() or 'definition' in f.lower()) for f in files):
            patterns.append("Step definitions for BDD")
        return patterns

    def _read_key_files(self, files: List[str]) -> Dict[str, str]:
        """Read content of key configuration files."""
        key_patterns = ['package.json', 'playwright.config', 'tsconfig', 'requirements.txt', 'conftest']
        contents = {}
        for f in files:
            if any(k in f.lower() for k in key_patterns):
                try:
                    full_path = os.path.join(self.repo_path, f)
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as fh:
                        contents[f] = fh.read()[:2000]  # First 2KB
                except Exception:
                    continue
        return contents

    def get_file_content(self, relative_path: str) -> str:
        """Read a specific file from the analyzed repository."""
        if not self.repo_path:
            return ""
        try:
            full_path = os.path.join(self.repo_path, relative_path)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def get_all_code_files(self) -> Dict[str, str]:
        """Get content of all code files for vectorstore indexing."""
        if not self.repo_path:
            return {}

        code_extensions = {'.ts', '.js', '.py', '.java', '.feature', '.json'}
        files = self._get_file_tree()
        code_files = {}

        for f in files:
            if Path(f).suffix.lower() in code_extensions:
                content = self.get_file_content(f)
                if content:
                    code_files[f] = content

        return code_files
