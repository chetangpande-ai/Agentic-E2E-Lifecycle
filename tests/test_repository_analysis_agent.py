from agents.repository_analysis_agent import RepositoryAnalysisAgent


def test_repo_tree_lists_code_paths_sorted():
    agent = object.__new__(RepositoryAnalysisAgent)
    tree = agent._repo_tree({
        "tests/b.spec.ts": "test",
        "package.json": "{}",
        "features/a.feature": "Feature: A",
    })

    assert tree.splitlines() == ["features/a.feature", "package.json", "tests/b.spec.ts"]


def test_sample_files_prioritizes_config_files():
    agent = object.__new__(RepositoryAnalysisAgent)
    samples = agent._sample_files({
        "tests/example.steps.ts": "steps",
        "package.json": "{\"devDependencies\": {}}",
        "playwright.config.ts": "config",
    })

    assert samples.index("--- package.json ---") < samples.index("--- tests/example.steps.ts ---")
    assert "--- playwright.config.ts ---" in samples
