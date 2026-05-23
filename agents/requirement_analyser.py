"""
Requirement Analyser Agent (Workflow 1).
Analyzes requirements from Jira for testability, gaps, and risks.
"""

import json
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import get_settings
from config.prompts.requirement_analyser import (
    REQUIREMENT_ANALYSIS_SYSTEM_PROMPT,
    REQUIREMENT_ANALYSIS_USER_PROMPT,
)
from models.requirement import Requirement, RequirementAnalysis
from utils.helpers import parse_json_from_llm
from utils.logger import logger, log_execution_start, log_execution_end, log_error, log_debug_data
import time


class RequirementAnalyserAgent:
    """Agent that analyzes requirements for testability and completeness."""

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=settings.groq_temperature,
            api_key=settings.groq_api_key,
        )

    def analyze(
        self,
        requirement: Requirement,
        feedback: str = "",
    ) -> RequirementAnalysis:
        """
        Analyze a requirement and produce a testability assessment.
        
        Args:
            requirement: The requirement to analyze.
            feedback: Optional HITL feedback for regeneration.
            
        Returns:
            RequirementAnalysis with scores, gaps, and recommendations.
        """
        logger.info(f"[bold blue]Analyzing requirement:[/bold blue] {requirement.id} - {requirement.title}")

        user_prompt = REQUIREMENT_ANALYSIS_USER_PROMPT.format(
            title=requirement.title,
            description=requirement.description or "Not provided",
            acceptance_criteria=requirement.acceptance_criteria or "Not provided",
            labels=", ".join(requirement.labels) if requirement.labels else "None",
            priority=requirement.priority,
        )

        if feedback:
            user_prompt += f"\n\n**IMPORTANT - Human Feedback for Regeneration**:\n{feedback}\nPlease address this feedback in your analysis."

        messages = [
            SystemMessage(content=REQUIREMENT_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        start_time = time.time()
        try:
            response = self.llm.invoke(messages)
            analysis_data = parse_json_from_llm(response.content)

            analysis = RequirementAnalysis(
                requirement_id=requirement.id,
                testability_score=analysis_data.get("testability_score", "MEDIUM"),
                testability_justification=analysis_data.get("testability_justification", ""),
                clarity_assessment=analysis_data.get("clarity_assessment", ""),
                functional_requirements=analysis_data.get("functional_requirements", []),
                non_functional_requirements=analysis_data.get("non_functional_requirements", []),
                acceptance_criteria_gaps=analysis_data.get("acceptance_criteria_gaps", []),
                recommended_test_types=analysis_data.get("recommended_test_types", []),
                risks_and_dependencies=analysis_data.get("risks_and_dependencies", []),
                suggested_clarifications=analysis_data.get("suggested_clarifications", []),
                edge_cases=analysis_data.get("edge_cases", []),
                estimated_test_cases_count=analysis_data.get("estimated_test_cases_count", 0),
                summary=analysis_data.get("summary", ""),
            )

            duration = time.time() - start_time
            log_execution_end(logger, f"RequirementAnalyser({requirement.id})", "SUCCESS", duration)
            log_debug_data(logger, "RequirementAnalysis", {
                "req_id": requirement.id,
                "testability": analysis.testability_score,
                "test_cases_est": analysis.estimated_test_cases_count,
                "gaps_count": len(analysis.acceptance_criteria_gaps),
            })
            return analysis

        except Exception as e:
            duration = time.time() - start_time
            log_error(logger, f"RequirementAnalyser({requirement.id})", e, {"duration": f"{duration:.2f}s"})
            raise
