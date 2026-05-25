from integrations.github_pr import GitHubPRClient
from models.script import FileType, GeneratedFile


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_commit_files_supplies_sha_when_file_exists():
    client = object.__new__(GitHubPRClient)
    calls = []

    def fake_api(method, path, json=None, expected=None):
        calls.append((method, path, json, expected))
        if method == "GET":
            return _Response(200, {"sha": "existing-sha"})
        return _Response(200)

    client._api = fake_api
    client._commit_files([
        GeneratedFile(path="features/generated-test-cases.feature", content="Feature: A", file_type=FileType.FEATURE)
    ], "branch")

    put_payload = calls[-1][2]
    assert put_payload["sha"] == "existing-sha"


def test_commit_files_omits_sha_when_file_is_new():
    client = object.__new__(GitHubPRClient)
    calls = []

    def fake_api(method, path, json=None, expected=None):
        calls.append((method, path, json, expected))
        if method == "GET":
            return _Response(404)
        return _Response(201)

    client._api = fake_api
    client._commit_files([
        GeneratedFile(path="tests/new.steps.ts", content="export {}", file_type=FileType.STEP_DEFINITION)
    ], "branch")

    put_payload = calls[-1][2]
    assert "sha" not in put_payload
