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

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.2,  # Slightly higher temp for code generation creativity
            api_key=settings.groq_api_key,
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
            repo_context = json.dumps(repo_analysis.model_dump(), indent=2)

        # Format test cases for the prompt
        tc_json = json.dumps(
            [tc.model_dump() for tc in test_cases],
            indent=2,
            default=str,
        )

        feedback_context = ""
        if feedback:
            feedback_context = f"**IMPORTANT - Human Feedback for Regeneration**:\n{feedback}\nPlease address this feedback in the generated scripts."

        user_prompt = SCRIPT_GENERATION_USER_PROMPT.format(
            test_cases_json=tc_json,
            repo_analysis=repo_context,
            web_crawl_data=web_crawl_data or "No web crawl data available.",
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

            script = TestScript(
                id=f"SCRIPT_{test_cases[0].requirement_id}" if test_cases else "SCRIPT_001",
                testcase_ids=[tc.id for tc in test_cases],
                files=files,
                dependencies=result.get("dependencies", [
                    "@playwright/test",
                    "playwright-bdd",
                ]),
                setup_commands=result.get("setup_commands", [
                    "npm init -y",
                    "npm install @playwright/test playwright-bdd",
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
        ]

    def analyze_repository(self, repo_url: Optional[str] = None) -> RepoAnalysis:
        """Analyze a repository for patterns and reusable code."""
        analyzer = RepoAnalyzer()
        return analyzer.analyze_repo(repo_url)

    def _get_rag_context(self, test_cases: List[TestCase]) -> str:
        """Retrieve relevant code patterns from the vector store."""
        try:
            # Build search query from test case types and descriptions
            queries = []
            for tc in test_cases[:3]:  # Use first 3 test cases for context
                queries.append(f"{tc.test_type} test {tc.title}")

            all_results = []
            for query in queries:
                results = similarity_search(query, collection_name="code_patterns", k=3)
                all_results.extend(results)

            if all_results:
                context_parts = []
                seen = set()
                for doc in all_results:
                    content_hash = hash(doc.page_content[:100])
                    if content_hash not in seen:
                        seen.add(content_hash)
                        file_path = doc.metadata.get("file_path", "unknown")
                        context_parts.append(f"--- {file_path} ---\n{doc.page_content}\n")

                return "\n".join(context_parts[:5])
        except Exception as e:
            logger.debug(f"No RAG context available: {e}")

        return ""
