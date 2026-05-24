from agents.script_generator import ScriptGeneratorAgent
from models.testcase import TestCase, TestStep


def test_fallback_script_files_are_generated_from_test_cases():
    test_case = TestCase(
        id="TC_001",
        requirement_id="KAN-5",
        title="Create user happy path",
        steps=[
            TestStep(
                step_number=1,
                action="Create user",
                input_data='{"email":"user@example.com"}',
                expected_result="User is created",
            )
        ],
        expected_result="User is created",
        tags=["api", "smoke"],
    )

    files = ScriptGeneratorAgent._build_fallback_files([test_case])

    assert len(files) == 4
    assert files[0].path == "features/generated-test-cases.feature"
    assert "Scenario: TC_001 Create user happy path" in files[0].content
    assert "TC_001" in files[2].content
