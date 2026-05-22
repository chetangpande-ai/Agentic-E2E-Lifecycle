"""
Common utility functions.
"""

import json
import re
from typing import Any, Dict, Optional


def parse_json_from_llm(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM response text.
    Handles cases where JSON is wrapped in markdown code blocks.
    """
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object/array in the text
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    # Return empty dict if nothing works
    return {}


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def generate_id(prefix: str, index: int) -> str:
    """Generate a formatted ID like TC_001, SC_001, etc."""
    return f"{prefix}_{index:03d}"


def format_test_steps_for_display(steps: list) -> str:
    """Format test steps into a readable string."""
    lines = []
    for step in steps:
        step_num = step.get("step_number", step.get("stepNumber", "?"))
        action = step.get("action", "")
        expected = step.get("expected_result", step.get("expectedResult", ""))
        lines.append(f"  {step_num}. {action}")
        if expected:
            lines.append(f"     → Expected: {expected}")
    return "\n".join(lines)
