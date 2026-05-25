from agents.script_generator import ScriptGeneratorAgent
from models.testcase import TestCase, TestStep
from models.script import RepoAnalysis


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

    assert len(files) == 6
    assert files[0].path == "features/generated-test-cases.feature"
    assert "Scenario: TC_001 Create user happy path" in files[0].content
    assert "TC_001" in files[2].content
    assert files[4].path == "package.json"
    assert "typescript" in files[4].content
    assert files[5].path == "tsconfig.json"


def test_script_generator_compacts_large_prompt_context():
    agent = object.__new__(ScriptGeneratorAgent)
    test_case = TestCase(
        id="TC_BIG_001",
        requirement_id="KAN-5",
        title="Create user with very large payload",
        preconditions=["precondition " + "x" * 500],
        steps=[
            TestStep(
                step_number=1,
                action="Submit create user request " + "a" * 500,
                input_data="{" + '"field":"' + "b" * 2000 + '"}',
                expected_result="User is created " + "c" * 500,
            )
        ],
        expected_result="Created " + "d" * 500,
        tags=["api", "smoke", "regression"],
    )
    repo_analysis = RepoAnalysis(
        framework="Playwright",
        test_pattern="BDD",
        language="TypeScript",
        reusable_components=[f"helper_{index}.ts" for index in range(20)],
        configuration_approach="config " + "x" * 2000,
        key_patterns=["pattern " + "y" * 500 for _ in range(20)],
        is_empty=False,
    )

    compact_cases = agent._compact_test_cases([test_case])
    compact_repo = agent._compact_repo_analysis(repo_analysis)

    assert len(str(compact_cases)) < 2500
    assert len(str(compact_repo)) < 3500
    assert len(compact_repo["reusable_components"]) == 8
