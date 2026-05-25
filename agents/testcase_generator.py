"""
Test Case Generator Agent (Workflow 2).
Generates detailed test cases from analyzed requirements.
"""

import json
from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import get_settings
from config.prompts.testcase_generator import (
    TESTCASE_GENERATION_SYSTEM_PROMPT,
    TESTCASE_GENERATION_USER_PROMPT,
)
from models.requirement import Requirement, RequirementAnalysis
from models.testcase import TestCase, TestStep
from utils.helpers import parse_json_from_llm
from utils.logger import logger, log_execution_end, log_error, log_debug_data
import time


class TestCaseGeneratorAgent:
    """Agent that generates comprehensive test cases from requirements."""

    TEXT_LIMIT = 2200
    EDGE_CASE_LIMIT = 10

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=settings.groq_temperature,
            api_key=settings.groq_api_key,
            max_tokens=1800,
        )

    def generate(
        self,
        requirement: Requirement,
        analysis: RequirementAnalysis,
        feedback: str = "",
    ) -> List[TestCase]:
        """
        Generate test cases from a requirement and its analysis.
        
        Args:
            requirement: The source requirement.
            analysis: The requirement analysis from Workflow 1.
            feedback: Optional HITL feedback for regeneration.
            
        Returns:
            List of TestCase objects.
        """
        logger.info(f"[bold green]Generating test cases for:[/bold green] {requirement.id}")
        start_time = time.time()

        feedback_context = ""
        if feedback:
            feedback_context = f"**IMPORTANT - Human Feedback for Regeneration**:\n{self._truncate(feedback, 900)}\nPlease address this feedback in the generated test cases."

        edge_cases = analysis.edge_cases[: self.EDGE_CASE_LIMIT] if analysis.edge_cases else []

        user_prompt = TESTCASE_GENERATION_USER_PROMPT.format(
            title=self._truncate(requirement.title, 300),
            description=self._truncate(requirement.description or "Not provided", self.TEXT_LIMIT),
            acceptance_criteria=self._truncate(requirement.acceptance_criteria or "Not provided", self.TEXT_LIMIT),
            analysis_summary=self._truncate(analysis.summary, 1000),
            recommended_test_types=self._truncate(", ".join(analysis.recommended_test_types), 500),
            edge_cases="\n".join(f"- {self._truncate(ec, 250)}" for ec in edge_cases) if edge_cases else "None identified",
            feedback_context=feedback_context,
        )

        messages = [
            SystemMessage(content=TESTCASE_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            log_debug_data(logger, "LLM Response (Raw)", response.content[:500])  # Log first 500 chars
            
            result = parse_json_from_llm(response.content)
            log_debug_data(logger, "Parsed JSON", str(result)[:500])  # Log parse result
            
            if not result:
                logger.warning("⚠️  JSON parsing returned empty result. Raw response may not be valid JSON.")
                log_debug_data(logger, "Full LLM Response for Failed Parse", response.content)
                raise ValueError("Failed to parse LLM response as JSON")

            test_cases = []
            raw_cases = result.get("test_cases", [])

            if not raw_cases:
                logger.warning(f"⚠️  LLM returned 0 test cases. Response had: {list(result.keys())}")
                log_debug_data(logger, "Empty test_cases Response", json.dumps(result, indent=2))
                raise ValueError("LLM returned empty test_cases array - check prompt and response format")

            for i, tc_data in enumerate(raw_cases):
                steps = []
                for step_index, step_data in enumerate(tc_data.get("steps", [])):
                    input_data = step_data.get("input_data", "")
                    if not isinstance(input_data, str):
                        input_data = json.dumps(input_data, ensure_ascii=False)

                    steps.append(TestStep(
                        step_number=step_data.get("step_number", step_index + 1),
                        action=step_data.get("action", ""),
                        input_data=input_data,
                        expected_result=step_data.get("expected_result", ""),
                    ))

                test_data = {
                    str(key): value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    for key, value in tc_data.get("test_data", {}).items()
                }
                test_type = tc_data.get("test_type", "UI")
                if test_type not in {"UI", "API", "DB", "Kafka", "MQ"}:
                    test_type = "UI"
                priority = tc_data.get("priority", "P2")
                if priority not in {"P0", "P1", "P2", "P3"}:
                    priority = "P2"

                test_case = TestCase(
                    id=tc_data.get("id", f"TC_{i+1:03d}"),
                    requirement_id=requirement.id,
                    title=tc_data.get("title", ""),
                    description=tc_data.get("description", ""),
                    preconditions=tc_data.get("preconditions", []),
                    test_type=test_type,
                    priority=priority,
                    steps=steps,
                    test_data=test_data,
                    expected_result=tc_data.get("expected_result", ""),
                    tags=tc_data.get("tags", []),
                )
                test_cases.append(test_case)

            elapsed = time.time() - start_time
            logger.info(f"✅ Generated {len(test_cases)} test cases in {elapsed:.2f}s")
            return test_cases

        except Exception as e:
            logger.error(f"❌ Error generating test cases: {str(e)}")
            log_error(logger, f"TestCaseGenerator({requirement.id})", e, {
                "requirement_id": requirement.id,
            })
            raise

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n...[truncated]"
