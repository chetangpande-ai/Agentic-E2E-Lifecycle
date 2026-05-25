"""
Repository analysis coding agent.
Reads cloned repository files and produces a structured automation profile.
"""

import json
from pathlib import Path
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config.prompts.script_generator import REPO_ANALYSIS_PROMPT
from config.settings import get_settings
from models.script import RepoAnalysis
from utils.helpers import parse_json_from_llm
from utils.logger import logger


class RepositoryAnalysisAgent:
    """Coding agent that reasons over existing test automation repository code."""

    MAX_SAMPLE_FILES = 12
    MAX_FILE_CHARS = 3000

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.0,
            api_key=settings.groq_api_key,
        )

    def analyze(self, code_files: Dict[str, str], heuristic_analysis: RepoAnalysis) -> RepoAnalysis:
        if not code_files:
            return heuristic_analysis

        repo_tree = self._repo_tree(code_files)
        sample_files = self._sample_files(code_files)
        prompt = REPO_ANALYSIS_PROMPT.format(
            repo_tree=repo_tree,
            sample_files=sample_files,
            heuristic_analysis=json.dumps(heuristic_analysis.model_dump(), indent=2),
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a senior coding agent analyzing an existing test automation repository. "
                    "Infer conventions from real files, prefer concrete observed patterns, and output only valid JSON."
                )
            ),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            data = parse_json_from_llm(response.content)
            return RepoAnalysis(
                framework=data.get("framework") or heuristic_analysis.framework,
                test_pattern=data.get("test_pattern") or heuristic_analysis.test_pattern,
                language=data.get("language") or heuristic_analysis.language,
                directory_structure=data.get("directory_structure") or heuristic_analysis.directory_structure,
                naming_conventions=data.get("naming_conventions") or heuristic_analysis.naming_conventions,
                reusable_components=data.get("reusable_components") or heuristic_analysis.reusable_components,
                configuration_approach=data.get("configuration_approach") or heuristic_analysis.configuration_approach,
                key_patterns=data.get("key_patterns") or heuristic_analysis.key_patterns,
                is_empty=False,
            )
        except Exception as exc:
            logger.warning(f"Repository coding-agent analysis failed; using heuristic analysis: {exc}")
            return heuristic_analysis

    def _repo_tree(self, code_files: Dict[str, str]) -> str:
        return "\n".join(sorted(code_files.keys())[:200])

    def _sample_files(self, code_files: Dict[str, str]) -> str:
        priority = [
            "package.json",
            "playwright.config.ts",
            "playwright.config.js",
            "tsconfig.json",
        ]

        selected = []
        paths = list(code_files.keys())
        for item in priority:
            selected.extend(path for path in paths if Path(path).name == item)

        selected.extend(
            path for path in paths
            if path not in selected and Path(path).suffix.lower() in {".feature", ".ts", ".js", ".json"}
        )

        samples = []
        for path in selected[: self.MAX_SAMPLE_FILES]:
            content = code_files[path][: self.MAX_FILE_CHARS]
            samples.append(f"--- {path} ---\n{content}")
        return "\n\n".join(samples)
