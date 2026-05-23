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

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=settings.groq_temperature,
            api_key=settings.groq_api_key,
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
            feedback_context = f"**IMPORTANT - Human Feedback for Regeneration**:\n{feedback}\nPlease address this feedback in the generated test cases."

        user_prompt = TESTCASE_GENERATION_USER_PROMPT.format(
            title=requirement.title,
            description=requirement.description or "Not provided",
            acceptance_criteria=requirement.acceptance_criteria or "Not provided",
            analysis_summary=analysis.summary,
            recommended_test_types=", ".join(analysis.recommended_test_types),
            edge_cases="\n".join(f"- {ec}" for ec in analysis.edge_cases) if analysis.edge_cases else "None identified",
            feedback_context=feedback_context,
        )

        messages = [
            SystemMessage(content=TESTCASE_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            result = parse_json_from_llm(response.content)

            test_cases = []
            raw_cases = result.get("test_cases", [])

            for i, tc_data in enumerate(raw_cases):
                steps = []
                for step_data in tc_data.get("steps", []):
                    steps.append(TestStep(
                        step_number=step_data.get("step_number", i + 1),
                        action=step_data.get("action", ""),
                        input_data=step_data.get("input_data", ""),
                        expected_result=step_data.get("expected_result", ""),
                    ))

                test_case = TestCase(
                    id=tc_data.get("id", f"TC_{i+1:03d}"),
                    requirement_id=requirement.id,
                    title=tc_data.get("title", ""),
                    description=tc_data.get("description", ""),
                    preconditions=tc_data.get("preconditions", []),
                    test_type=tc_data.get("test_type", "UI"),
                    priority=tc_data.get("priority", "P2"),
                    steps=steps,
                    test_data=tc_data.get("test_data", {}),
                    expected_result=tc_data.get("expected_result", ""),
                    tags=tc_data.get("tags", []),
                )
                test_cases.append(test_case)

            logger.info(f"Generated {len(test_cases)} test cases")
            return test_cases

        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            raise
