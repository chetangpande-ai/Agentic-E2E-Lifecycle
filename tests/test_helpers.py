from utils.helpers import parse_json_from_llm


def test_parse_json_repairs_repeat_expression():
    payload = parse_json_from_llm('{"value": "A".repeat(5)}')

    assert payload == {"value": "AAAAA"}


def test_parse_json_repairs_repeat_expression_in_code_block():
    payload = parse_json_from_llm(
        """```json
{"test_cases": [{"test_data": {"firstName": "A".repeat(3)}}]}
```"""
    )

    assert payload["test_cases"][0]["test_data"]["firstName"] == "AAA"


def test_parse_json_recovers_complete_cases_from_truncated_array():
    payload = parse_json_from_llm(
        """{"test_cases": [
{"id": "TC_001", "title": "Complete"},
{"id": "TC_002", "title": "Also complete"},
{"id": "TC_003", "title": "Truncated"
"""
    )

    assert [case["id"] for case in payload["test_cases"]] == ["TC_001", "TC_002"]
