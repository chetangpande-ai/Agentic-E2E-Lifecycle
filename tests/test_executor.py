from agents.test_executor import TestExecutorAgent as _TestExecutorAgent
from models.script import FileType, GeneratedFile, TestScript as _TestScript


def test_required_packages_include_script_dependencies_and_imports():
    script = _TestScript(
        dependencies=["@playwright/test"],
        files=[
            GeneratedFile(
                path="tests/example.steps.ts",
                content="""
import { test } from '@playwright/test';
import { createBdd } from 'playwright-bdd';
import helper from './helper';
import fs from 'node:fs';
const axios = require('axios');
""",
                file_type=FileType.STEP_DEFINITION,
            )
        ],
    )

    assert _TestExecutorAgent._required_packages(script) == {
        "@playwright/test",
        "playwright-bdd",
        "axios",
    }


def test_declared_packages_include_all_package_json_dependency_sections():
    package_json = {
        "dependencies": {"axios": "^1.0.0"},
        "devDependencies": {"@playwright/test": "^1.0.0"},
        "peerDependencies": {"playwright-bdd": "^8.0.0"},
        "optionalDependencies": {"dotenv": "^16.0.0"},
    }

    assert _TestExecutorAgent._declared_packages(package_json) == {
        "axios",
        "@playwright/test",
        "playwright-bdd",
        "dotenv",
    }


def test_sync_main_branch_skips_pull_for_empty_repository(monkeypatch, tmp_path):
    agent = _TestExecutorAgent()
    monkeypatch.setattr(agent, "_remote_heads", lambda repo_url: set())

    agent._sync_main_branch(str(tmp_path))

    assert list(tmp_path.iterdir()) == []


def test_sync_main_branch_requires_main_for_non_empty_repository(monkeypatch, tmp_path):
    agent = _TestExecutorAgent()
    monkeypatch.setattr(agent, "_remote_heads", lambda repo_url: {"develop"})

    try:
        agent._sync_main_branch(str(tmp_path))
    except RuntimeError as exc:
        assert "no main branch" in str(exc)
    else:
        raise AssertionError("Expected missing main branch to fail")
