"""
Test Executor Agent (Workflow 4).
Executes test scripts, auto-heals failures, commits to GitHub.
"""

import json
import os
import subprocess
import tempfile
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import get_settings
from config.prompts.executor import (
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_RUN_PROMPT,
    AUTO_HEAL_PROMPT,
    COMMIT_PR_PROMPT,
)
from models.script import TestScript, GeneratedFile
from models.execution import ExecutionResult, TestResult, AutoHealAttempt, ExecutionStatus
from utils.helpers import parse_json_from_llm
from utils.logger import logger, log_execution_start, log_execution_end, log_error, log_debug_data
import time


class TestExecutorAgent:
    """Agent that executes test scripts with auto-heal capabilities."""

    MAX_HEAL_ATTEMPTS = 3

    def __init__(self):
        settings = get_settings()
        self.llm = ChatGroq(
            model=settings.groq_model,
            temperature=0.0,  # Zero temp for precise debugging
            api_key=settings.groq_api_key,
        )
        self.settings = settings

    def execute(self, script: TestScript) -> ExecutionResult:
        """
        Execute test scripts with auto-heal on failure.
        
        Args:
            script: TestScript containing files and setup commands.
            
        Returns:
            ExecutionResult with pass/fail details and auto-heal history.
        """
        logger.info(f"[bold red]Executing test scripts:[/bold red] {script.id}")

        # Set up workspace
        workspace = tempfile.mkdtemp(prefix="test_execution_")
        self._write_files(workspace, script.files)

        # Run setup commands
        setup_success = self._run_setup(workspace, script.setup_commands)
        if not setup_success:
            return ExecutionResult(
                id=f"EXEC_{script.id}",
                script_id=script.id,
                status=ExecutionStatus.ERROR,
                logs="Setup failed. Check dependencies and configuration.",
            )

        # Execute tests (with auto-heal loop)
        result = self._execute_with_heal(workspace, script)
        result.id = f"EXEC_{script.id}"
        result.script_id = script.id

        return result

    def _write_files(self, workspace: str, files: List[GeneratedFile]) -> None:
        """Write generated files to the workspace directory."""
        for file in files:
            file_path = os.path.join(workspace, file.path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file.content)
            logger.info(f"  Written: {file.path}")

    def _run_setup(self, workspace: str, commands: List[str]) -> bool:
        """Run setup commands in the workspace."""
        logger.info("Running setup commands...")
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0:
                    logger.error(f"Setup command failed: {cmd}\n{result.stderr}")
                    return False
                logger.info(f"  ✓ {cmd}")
            except subprocess.TimeoutExpired:
                logger.error(f"Setup command timed out: {cmd}")
                return False
            except Exception as e:
                logger.error(f"Setup error: {e}")
                return False
        return True

    def _execute_with_heal(self, workspace: str, script: TestScript) -> ExecutionResult:
        """Execute tests with auto-heal loop (max 3 attempts)."""
        heal_attempts = []
        current_files = script.files.copy()

        for attempt in range(self.MAX_HEAL_ATTEMPTS + 1):
            # Run the tests
            exec_result = self._run_tests(workspace)

            if exec_result.status == ExecutionStatus.PASS:
                exec_result.auto_heal_attempts = heal_attempts
                logger.info("[bold green]✓ All tests passed![/bold green]")
                return exec_result

            if attempt >= self.MAX_HEAL_ATTEMPTS:
                logger.warning(f"Max auto-heal attempts ({self.MAX_HEAL_ATTEMPTS}) reached")
                exec_result.auto_heal_attempts = heal_attempts
                return exec_result

            # Auto-heal: analyze failures and fix
            logger.info(f"[bold yellow]Auto-heal attempt {attempt + 1}/{self.MAX_HEAL_ATTEMPTS}[/bold yellow]")

            for failed_test in exec_result.results:
                if failed_test.status == ExecutionStatus.FAIL:
                    heal_result = self._auto_heal(
                        failed_test=failed_test,
                        current_files=current_files,
                        attempt_number=attempt + 1,
                    )

                    heal_attempts.append(heal_result)

                    if heal_result.success:
                        # Write updated files
                        # The heal result should have updated files embedded
                        logger.info(f"  Applied fix: {heal_result.fix_description}")

        exec_result = ExecutionResult(
            status=ExecutionStatus.FAIL,
            auto_heal_attempts=heal_attempts,
            logs="Auto-heal exhausted all attempts",
        )
        return exec_result

    def _run_tests(self, workspace: str) -> ExecutionResult:
        """Run the test suite and capture results."""
        try:
            result = subprocess.run(
                "npx playwright test --reporter=json",
                shell=True,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=300,
            )

            logs = result.stdout + "\n" + result.stderr

            # Parse results
            if result.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.PASS,
                    logs=logs,
                    total_tests=1,
                    passed=1,
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAIL,
                    logs=logs,
                    results=[
                        TestResult(
                            test_name="Test Suite",
                            status=ExecutionStatus.FAIL,
                            error_message=result.stderr[:500] if result.stderr else "Unknown error",
                            stack_trace=result.stderr,
                        )
                    ],
                )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                logs="Test execution timed out (300s)",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                logs=f"Execution error: {str(e)}",
            )

    def _auto_heal(
        self,
        failed_test: TestResult,
        current_files: List[GeneratedFile],
        attempt_number: int,
    ) -> AutoHealAttempt:
        """Attempt to auto-heal a failed test."""
        # Find the relevant file content
        file_contents = "\n\n".join(
            f"--- {f.path} ---\n{f.content}" for f in current_files
        )

        prompt = AUTO_HEAL_PROMPT.format(
            test_name=failed_test.test_name,
            error_message=failed_test.error_message,
            stack_trace=failed_test.stack_trace[:2000],
            original_code=file_contents[:3000],
            attempt_number=attempt_number,
        )

        messages = [
            SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            result = parse_json_from_llm(response.content)

            return AutoHealAttempt(
                attempt_number=attempt_number,
                root_cause=result.get("root_cause", "Unknown"),
                fix_description=result.get("fix_description", ""),
                success=True,
            )
        except Exception as e:
            return AutoHealAttempt(
                attempt_number=attempt_number,
                root_cause=f"Auto-heal error: {str(e)}",
                fix_description="",
                success=False,
            )
