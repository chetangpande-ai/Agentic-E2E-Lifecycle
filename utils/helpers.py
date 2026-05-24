"""
Common utility functions.
"""

import json
import re
from typing import Any, Dict, Optional


def _repair_json_text(text: str) -> str:
    """Repair common LLM JSON slips that are deterministic to fix."""
    repeat_pattern = re.compile(r'"((?:\\.|[^"\\])*)"\.repeat\(\s*(\d{1,4})\s*\)')

    def expand_repeat(match: re.Match) -> str:
        value = json.loads(f'"{match.group(1)}"')
        count = int(match.group(2))
        return json.dumps(value * count)

    return repeat_pattern.sub(expand_repeat, text)


def _parse_partial_test_cases(text: str) -> Dict[str, Any]:
    """Recover complete test case objects from a truncated test_cases array."""
    marker = re.search(r'"test_cases"\s*:\s*\[', text)
    if not marker:
        return {}

    cases = []
    depth = 0
    start = None
    in_string = False
    escape = False

    for index in range(marker.end(), len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    cases.append(json.loads(text[start:index + 1]))
                except json.JSONDecodeError:
                    pass
                start = None
        elif char == "]" and depth == 0:
            break

    return {"test_cases": cases} if cases else {}


def parse_json_from_llm(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from LLM response text.
    Handles cases where JSON is wrapped in markdown code blocks.
    Returns empty dict if parsing fails.
    """
    # Try to find JSON in code blocks first
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()

    text = _repair_json_text(text)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    partial = _parse_partial_test_cases(text)
    if partial:
        return partial

    # Try to find JSON object/array in the text
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            repaired = _repair_json_text(match.group())
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                partial = _parse_partial_test_cases(repaired)
                if partial:
                    return partial

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
