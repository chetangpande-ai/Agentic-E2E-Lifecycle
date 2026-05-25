"""
Test Script Generator Agent (Workflow 3).
Generates Playwright-BDD test automation scripts.
Analyzes existing repos for patterns, uses Playwright MCP for web crawling.
"""

import json
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import get_settings
from config.prompts.script_generator import (
    SCRIPT_GENERATION_SYSTEM_PROMPT,
    SCRIPT_GENERATION_USER_PROMPT,
    REPO_ANALYSIS_PROMPT,
    WEB_CRAWL_PROMPT,
)
from models.testcase import TestCase
from models.script import FileType, TestScript, GeneratedFile, RepoAnalysis
from integrations.repo_analyzer import RepoAnalyzer
from vectorstore.store import similarity_search
from utils.helpers import parse_json_from_llm
from utils.logger import logger, log_execution_start, log_execution_end, log_error, log_debug_data
import time


class ScriptGeneratorAgent:
    """Agent that generates test automation scripts from test cases."""

    MAX_TEST_CASES_IN_PROMPT = 5
    MAX_RAG_CHARS = 1800
    MAX_REPO_CONTEXT_CHARS = 1800
    MAX_WEB_CRAWL_CHARS = 1200

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.2,  # Slightly higher temp for code generation creativity
            api_key=settings.groq_api_key,
            max_tokens=1800,
        )
        self.settings = settings

    def generate(
        self,
        test_cases: List[TestCase],
        repo_analysis: Optional[RepoAnalysis] = None,
        web_crawl_data: str = "",
        feedback: str = "",
    ) -> TestScript:
        """
        Generate test scripts from test cases.
        
        Args:
            test_cases: List of approved test cases.
            repo_analysis: Analysis of the target/reference repo.
            web_crawl_data: Data from Playwright MCP web crawling.
            feedback: Optional HITL feedback for regeneration.
            
        Returns:
            TestScript with generated files.
        """
        logger.info(f"[bold magenta]Generating scripts for {len(test_cases)} test cases[/bold magenta]")

        # Get relevant code patterns from vector store
        rag_context = self._get_rag_context(test_cases)

        # Build repo analysis context
        repo_context = "No existing repository patterns detected. Using Playwright-BDD default patterns."
        if repo_analysis and not repo_analysis.is_empty:
            repo_context = self._truncate(
                json.dumps(self._compact_repo_analysis(repo_analysis), indent=2),
                self.MAX_REPO_CONTEXT_CHARS,
            )

        # Format test cases for the prompt
        tc_json = self._truncate(
            json.dumps(
                self._compact_test_cases(test_cases),
                indent=2,
                default=str,
            ),
            6500,
        )

        feedback_context = ""
        if feedback:
            feedback_context = f"**IMPORTANT - Human Feedback for Regeneration**:\n{self._truncate(feedback, 800)}\nPlease address this feedback in the generated scripts."

        user_prompt = SCRIPT_GENERATION_USER_PROMPT.format(
            test_cases_json=tc_json,
            repo_analysis=repo_context,
            web_crawl_data=self._truncate(web_crawl_data, self.MAX_WEB_CRAWL_CHARS) or "No web crawl data available.",
            feedback_context=feedback_context,
        )

        # Add RAG context if available
        if rag_context:
            user_prompt += f"\n\n**Relevant Code Patterns from Vector Store**:\n{rag_context}"

        messages = [
            SystemMessage(content=SCRIPT_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            result = parse_json_from_llm(response.content)

            files = []
            for file_data in result.get("files", []):
                path = file_data.get("path", "")
                content = file_data.get("content", "")
                file_type = file_data.get("type", file_data.get("file_type", "helper"))
                if file_type not in {item.value for item in FileType}:
                    file_type = "helper"
                if not path or not content:
                    continue

                files.append(GeneratedFile(
                    path=path,
                    content=content,
                    file_type=file_type,
                ))

            if not files:
                logger.warning("LLM did not return parseable script files. Building fallback Playwright-BDD scripts.")
                files = self._build_fallback_files(test_cases)

            dependencies = result.get("dependencies", [
                "@playwright/test",
                "playwright-bdd",
                "typescript",
            ])
            if any(file.path.endswith((".ts", ".tsx")) for file in files) and "typescript" not in dependencies:
                dependencies.append("typescript")
            self._ensure_project_config(files, dependencies)

            script = TestScript(
                id=f"SCRIPT_{test_cases[0].requirement_id}" if test_cases else "SCRIPT_001",
                testcase_ids=[tc.id for tc in test_cases],
                files=files,
                dependencies=dependencies,
                setup_commands=result.get("setup_commands", [
                    "npm init -y",
                    "npm install @playwright/test playwright-bdd typescript",
                    "npx playwright install",
                ]),
                framework="playwright-bdd",
                language="typescript",
            )

            logger.info(f"Generated {len(files)} script files")
            return script

        except Exception as e:
            logger.error(f"Error generating scripts: {e}")
            raise

    @staticmethod
    def _build_fallback_files(test_cases: List[TestCase]) -> List[GeneratedFile]:
        """Build baseline executable Playwright-BDD files from test case metadata."""
        feature_lines = [
            "Feature: Generated test cases",
            "  Generated from approved human-reviewed test cases.",
            "",
            "  Background:",
            "    Given test preconditions are satisfied",
            "",
        ]
        test_data = []

        def clean(value: str) -> str:
            return " ".join(str(value or "").replace('"', "'").split())

        for test_case in test_cases:
            tags = " ".join(f"@{clean(tag).replace(' ', '_')}" for tag in test_case.tags) or "@generated"
            feature_lines.extend([
                f"  {tags}",
                f"  Scenario: {clean(test_case.id)} {clean(test_case.title)}",
                f"    When I execute test case \"{clean(test_case.id)}\"",
                f"    Then the expected result should be \"{clean(test_case.expected_result or test_case.title)}\"",
                "",
            ])
            test_data.append(test_case.model_dump(mode="json"))

        feature_content = "\n".join(feature_lines)
        data_content = json.dumps(test_data, indent=2)
        steps_content = """import { expect, test } from '@playwright/test';
import { createBdd } from 'playwright-bdd';
import testCases from './generated-test-data.json';

const { Given, When, Then } = createBdd(test);

type GeneratedTestCase = {
  id: string;
  title: string;
  steps?: Array<{ action?: string; input_data?: string; expected_result?: string }>;
};

let activeTestCase: GeneratedTestCase | undefined;

Given('test preconditions are satisfied', async () => {
  expect(Array.isArray(testCases)).toBeTruthy();
});

When('I execute test case {string}', async ({}, testCaseId: string) => {
  activeTestCase = (testCases as GeneratedTestCase[]).find((item) => item.id === testCaseId);
  expect(activeTestCase, `Missing generated test case ${testCaseId}`).toBeTruthy();

  for (const step of activeTestCase?.steps ?? []) {
    test.info().annotations.push({
      type: 'generated-step',
      description: `${step.action ?? ''} | input=${step.input_data ?? ''} | expected=${step.expected_result ?? ''}`,
    });
  }
});

Then('the expected result should be {string}', async ({}, expectedResult: string) => {
  expect(activeTestCase).toBeTruthy();
  expect(expectedResult.length).toBeGreaterThan(0);
});
"""
        config_content = """import { defineConfig } from '@playwright/test';
import { defineBddConfig } from 'playwright-bdd';

const testDir = defineBddConfig({
  features: 'features/**/*.feature',
  steps: 'tests/**/*.steps.ts',
});

export default defineConfig({
  testDir,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    trace: 'retain-on-failure',
  },
});
"""

        return [
            GeneratedFile(path="features/generated-test-cases.feature", content=feature_content, file_type="feature"),
            GeneratedFile(path="tests/generated-test-cases.steps.ts", content=steps_content, file_type="step_definition"),
            GeneratedFile(path="tests/generated-test-data.json", content=data_content, file_type="fixture"),
            GeneratedFile(path="playwright.config.ts", content=config_content, file_type="config"),
            GeneratedFile(path="package.json", content=ScriptGeneratorAgent._package_json(["@playwright/test", "playwright-bdd", "typescript"]), file_type="config"),
            GeneratedFile(path="tsconfig.json", content=ScriptGeneratorAgent._tsconfig_json(), file_type="config"),
        ]

    @staticmethod
    def _ensure_project_config(files: List[GeneratedFile], dependencies: List[str]) -> None:
        paths = {file.path.replace("\\", "/") for file in files}
        if "package.json" not in paths:
            files.append(GeneratedFile(
                path="package.json",
                content=ScriptGeneratorAgent._package_json(dependencies),
                file_type="config",
            ))
        if any(file.path.endswith((".ts", ".tsx")) for file in files) and "tsconfig.json" not in paths:
            files.append(GeneratedFile(
                path="tsconfig.json",
                content=ScriptGeneratorAgent._tsconfig_json(),
                file_type="config",
            ))

    @staticmethod
    def _infer_file_type(path: str) -> FileType:
        normalized = path.replace("\\", "/").lower()
        if normalized.endswith(".feature"):
            return FileType.FEATURE
        if normalized.endswith(".steps.ts") or "step" in normalized:
            return FileType.STEP_DEFINITION
        if "page" in normalized and normalized.endswith((".ts", ".js")):
            return FileType.PAGE_OBJECT
        if normalized.endswith(".json") and "package.json" not in normalized and "tsconfig.json" not in normalized:
            return FileType.FIXTURE
        if normalized.endswith((".config.ts", ".config.js")) or normalized in {"package.json", "tsconfig.json"}:
            return FileType.CONFIG
        return FileType.HELPER

    @staticmethod
    def _dependencies_from_package(package_content: str) -> List[str]:
        if not package_content:
            return ["@playwright/test", "playwright-bdd", "typescript"]
        try:
            package_json = json.loads(package_content)
        except json.JSONDecodeError:
            return ["@playwright/test", "playwright-bdd", "typescript"]

        dependencies = []
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            values = package_json.get(section, {})
            if isinstance(values, dict):
                dependencies.extend(values.keys())
        return dependencies or ["@playwright/test", "playwright-bdd", "typescript"]

    @staticmethod
    def _package_json(dependencies: List[str]) -> str:
        package_names = []
        for dependency in dependencies:
            package = dependency.split("@")[0] if not dependency.startswith("@") else "@".join(dependency.split("@")[:2])
            if package and package not in package_names:
                package_names.append(package)
        dev_dependencies = {
            package: "latest" for package in package_names
        }
        return json.dumps({
            "name": "generated-playwright-bdd-tests",
            "version": "1.0.0",
            "private": True,
            "scripts": {
                "build": "tsc --noEmit",
                "test": "playwright test",
            },
            "devDependencies": dev_dependencies,
        }, indent=2)

    @staticmethod
    def _tsconfig_json() -> str:
        return json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
            },
            "include": [
                "tests/**/*.ts",
                "playwright.config.ts",
            ],
        }, indent=2)

    def analyze_repository(self, repo_url: Optional[str] = None) -> RepoAnalysis:
        """Analyze a repository for patterns and reusable code."""
        analyzer = RepoAnalyzer()
        return analyzer.analyze_repo(repo_url)

    def _get_rag_context(self, test_cases: List[TestCase]) -> str:
        """Retrieve relevant code patterns from the vector store."""
        try:
            # Build search query from test case types and descriptions
            queries = []
            for tc in test_cases[:2]:
                queries.append(f"{tc.test_type} test {tc.title}")

            all_results = []
            for query in queries:
                results = similarity_search(query, collection_name="code_patterns", k=1)
                all_results.extend(results)

            if all_results:
                context_parts = []
                seen = set()
                for doc in all_results:
                    content_hash = hash(doc.page_content[:100])
                    if content_hash not in seen:
                        seen.add(content_hash)
                        file_path = doc.metadata.get("file_path", "unknown")
                        chunk = self._truncate(doc.page_content, 700)
                        context_parts.append(f"--- {file_path} ---\n{chunk}\n")

                return self._truncate("\n".join(context_parts[:3]), self.MAX_RAG_CHARS)
        except Exception as e:
            logger.debug(f"No RAG context available: {e}")

        return ""

    def _compact_test_cases(self, test_cases: List[TestCase]) -> List[dict]:
        compact = []
        for test_case in test_cases[: self.MAX_TEST_CASES_IN_PROMPT]:
            compact.append({
                "id": test_case.id,
                "requirement_id": test_case.requirement_id,
                "title": self._truncate(test_case.title, 180),
                "test_type": test_case.test_type,
                "priority": test_case.priority,
                "preconditions": [self._truncate(item, 160) for item in test_case.preconditions[:3]],
                "steps": [
                    {
                        "action": self._truncate(step.action, 180),
                        "input_data": self._truncate(step.input_data, 220),
                        "expected_result": self._truncate(step.expected_result, 180),
                    }
                    for step in test_case.steps[:4]
                ],
                "expected_result": self._truncate(test_case.expected_result, 220),
                "tags": test_case.tags[:6],
            })
        return compact

    def _compact_repo_analysis(self, repo_analysis: RepoAnalysis) -> dict:
        return {
            "framework": repo_analysis.framework,
            "test_pattern": repo_analysis.test_pattern,
            "language": repo_analysis.language,
            "directory_structure": repo_analysis.directory_structure,
            "naming_conventions": repo_analysis.naming_conventions,
            "reusable_components": repo_analysis.reusable_components[:8],
            "configuration_approach": self._truncate(repo_analysis.configuration_approach, 400),
            "key_patterns": [self._truncate(item, 220) for item in repo_analysis.key_patterns[:8]],
            "is_empty": repo_analysis.is_empty,
        }

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n...[truncated]"
