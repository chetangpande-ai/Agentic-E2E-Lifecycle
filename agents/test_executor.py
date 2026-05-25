"""
Test Executor Agent (Workflow 4).
Validates generated scripts against the target repository before PR creation.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Set

import git

from config.settings import get_settings
from models.execution import ExecutionResult, ExecutionStatus, TestResult
from models.script import GeneratedFile, TestScript
from utils.logger import logger


class TestExecutorAgent:
    """Agent that validates generated scripts are merge-ready for the target repo."""

    IMPORT_RE = re.compile(
        r"(?:import\s+(?:[^'\"\n]+\s+from\s+)?|require\()\s*['\"]([^'\"]+)['\"]"
    )
    NODE_BUILTINS = {
        "assert",
        "buffer",
        "child_process",
        "crypto",
        "events",
        "fs",
        "http",
        "https",
        "os",
        "path",
        "process",
        "stream",
        "url",
        "util",
    }

    def __init__(self):
        self.settings = get_settings()

    def execute(self, script: TestScript) -> ExecutionResult:
        """
        Validate generated scripts against the latest main branch.

        Checks:
        1. Clone/pull the latest target main branch and apply generated files.
        2. Confirm generated code has no syntax/compile errors.
        3. Confirm imported/generated dependencies are declared in package.json.
        """
        logger.info(f"[bold red]Validating generated scripts:[/bold red] {script.id}")
        workspace = tempfile.mkdtemp(prefix="script_validation_")
        checks: List[TestResult] = []
        logs: List[str] = []

        try:
            sync_message = self._sync_main_branch(workspace)
            self._write_files(workspace, script.files)
            checks.append(self._pass("main_branch_sync", sync_message))

            dependency_errors = self._validate_package_dependencies(workspace, script)
            if dependency_errors:
                checks.append(self._fail("package_json_dependencies", "\n".join(dependency_errors)))
            else:
                checks.append(self._pass("package_json_dependencies", "Required libraries are declared."))

            compile_errors = self._validate_compile_state(workspace, script.files)
            if compile_errors:
                checks.append(self._fail("syntax_compile", compile_errors))
            else:
                checks.append(self._pass("syntax_compile", "Generated code is in a compiled state."))

            failed = [check for check in checks if check.status != ExecutionStatus.PASS]
            status = ExecutionStatus.FAIL if failed else ExecutionStatus.PASS
            return ExecutionResult(
                status=status,
                total_tests=len(checks),
                passed=len(checks) - len(failed),
                failed=len(failed),
                results=checks,
                logs="\n".join(logs + [check.error_message or check.test_name for check in checks]),
            )
        except Exception as exc:
            logger.error(f"Executor validation failed: {exc}")
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                total_tests=len(checks) + 1,
                passed=sum(1 for check in checks if check.status == ExecutionStatus.PASS),
                failed=1,
                results=checks + [self._fail("main_branch_sync", str(exc))],
                logs=str(exc),
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _sync_main_branch(self, workspace: str) -> str:
        """Prepare a workspace from the target repo.

        Empty repositories do not have a main branch yet, so validation starts
        from a blank workspace. Non-empty repositories must validate against
        the configured main branch.
        """
        repo_url = f"https://github.com/{self.settings.github_target_repo}.git"
        base_branch = self.settings.github_target_branch or "main"
        heads = self._remote_heads(repo_url)

        if not heads:
            logger.info(f"Target repository is empty; skipping pull from {base_branch}")
            return f"Target repository is empty; skipped pull from {base_branch}."

        if base_branch not in heads:
            available = ", ".join(sorted(heads))
            raise RuntimeError(f"Target repository has branches ({available}) but no {base_branch} branch")

        logger.info(f"Pulling latest {base_branch} from {repo_url}")
        repo = git.Repo.clone_from(repo_url, workspace, branch=base_branch)
        repo.git.checkout(base_branch)
        repo.remotes.origin.pull(base_branch)

        unresolved = list(Path(workspace).rglob("*"))
        conflict_files = [
            path for path in unresolved
            if path.is_file() and not self._is_ignored_path(path, workspace) and self._has_conflict_markers(path)
        ]
        if conflict_files:
            files = ", ".join(str(path.relative_to(workspace)) for path in conflict_files[:10])
            raise RuntimeError(f"Unresolved merge conflict markers found after pulling main: {files}")

        return f"Pulled latest {base_branch} and applied generated files."

    def _remote_heads(self, repo_url: str) -> Set[str]:
        """Return branch names published by the remote repository."""
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Could not inspect target repository branches: {result.stderr.strip()}")

        heads = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                heads.add(parts[1].removeprefix("refs/heads/"))
        return heads

    def _write_files(self, workspace: str, files: List[GeneratedFile]) -> None:
        """Write generated files into the cloned repository workspace."""
        for file in files:
            file_path = Path(workspace, file.path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding="utf-8")
            logger.info(f"  Written: {file.path}")

    def _validate_package_dependencies(self, workspace: str, script: TestScript) -> List[str]:
        package_path = Path(workspace, "package.json")
        required = self._required_packages(script)
        if not required:
            return []
        if not package_path.exists():
            return [f"package.json is missing; required packages: {', '.join(sorted(required))}"]

        try:
            package_json = json.loads(package_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [f"package.json is not valid JSON: {exc}"]

        declared = self._declared_packages(package_json)
        missing = sorted(required - declared)
        if missing:
            return [f"Missing package.json dependencies: {', '.join(missing)}"]
        return []

    def _validate_compile_state(self, workspace: str, files: List[GeneratedFile]) -> str:
        package_path = Path(workspace, "package.json")
        package_json: Dict = {}
        if package_path.exists():
            try:
                package_json = json.loads(package_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return f"package.json is not valid JSON: {exc}"

        install_error = self._run_command(["npm", "install", "--ignore-scripts"], workspace, timeout=180)
        if install_error:
            return install_error

        scripts = package_json.get("scripts", {}) if isinstance(package_json, dict) else {}
        if "build" in scripts:
            return self._run_command(["npm", "run", "build"], workspace, timeout=180)

        has_ts = any(Path(file.path).suffix in {".ts", ".tsx"} for file in files)
        if has_ts:
            if Path(workspace, "tsconfig.json").exists():
                return self._run_command(["npx", "tsc", "--noEmit"], workspace, timeout=180)
            ts_files = [file.path for file in files if Path(file.path).suffix in {".ts", ".tsx"}]
            return self._run_command(
                [
                    "npx",
                    "tsc",
                    "--noEmit",
                    "--skipLibCheck",
                    "--moduleResolution",
                    "bundler",
                    "--module",
                    "esnext",
                    "--target",
                    "es2020",
                    "--resolveJsonModule",
                    "--esModuleInterop",
                    *ts_files,
                ],
                workspace,
                timeout=180,
            )

        js_files = [file.path for file in files if Path(file.path).suffix in {".js", ".jsx", ".mjs", ".cjs"}]
        for js_file in js_files:
            error = self._run_command(["node", "--check", js_file], workspace, timeout=60)
            if error:
                return error

        for file in files:
            if Path(file.path).suffix == ".json":
                try:
                    json.loads(Path(workspace, file.path).read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    return f"{file.path} is not valid JSON: {exc}"

        return ""

    def _run_command(self, command: List[str], workspace: str, timeout: int) -> str:
        executable = shutil.which(command[0])
        if not executable:
            return f"Required command not available: {command[0]}"

        try:
            result = subprocess.run(
                [executable, *command[1:]],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError as exc:
            return f"Required command not available: {exc.filename}"
        except subprocess.TimeoutExpired:
            return f"Command timed out: {' '.join(command)}"

        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr).strip()
            return f"Command failed: {' '.join(command)}\n{output[-4000:]}"
        return ""

    @classmethod
    def _required_packages(cls, script: TestScript) -> Set[str]:
        packages = {cls._package_name(dep) for dep in script.dependencies if dep}
        for file in script.files:
            if Path(file.path).suffix not in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
                continue
            for module in cls.IMPORT_RE.findall(file.content):
                package = cls._package_name(module)
                if package:
                    packages.add(package)
        return {package for package in packages if package}

    @classmethod
    def _package_name(cls, module: str) -> str:
        if not module or module.startswith((".", "/", "#")):
            return ""
        if module.startswith("node:"):
            return ""
        first = module.split("/")[0]
        if first in cls.NODE_BUILTINS:
            return ""
        if module.startswith("@"):
            parts = module.split("/")
            return "/".join(parts[:2]) if len(parts) >= 2 else module
        return first

    @staticmethod
    def _declared_packages(package_json: Dict) -> Set[str]:
        declared: Set[str] = set()
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            values = package_json.get(section, {})
            if isinstance(values, dict):
                declared.update(values.keys())
        return declared

    @staticmethod
    def _has_conflict_markers(path: Path) -> bool:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False
        return "<<<<<<< " in content or ("=======" in content and ">>>>>>> " in content)

    @staticmethod
    def _is_ignored_path(path: Path, workspace: str) -> bool:
        rel = path.relative_to(workspace)
        return any(part in {".git", "node_modules"} for part in rel.parts)

    @staticmethod
    def _pass(name: str, message: str) -> TestResult:
        return TestResult(test_name=name, status=ExecutionStatus.PASS, error_message=message)

    @staticmethod
    def _fail(name: str, message: str) -> TestResult:
        return TestResult(test_name=name, status=ExecutionStatus.FAIL, error_message=message)
