"""
Prompt templates for the Test Executor Agent.
"""

EXECUTOR_SYSTEM_PROMPT = """You are an expert Test Automation Engineer responsible for validating generated test scripts 
before they are sent to GitHub.

Your responsibilities:
1. Pull the latest main branch of the target repository and detect unresolved conflicts
2. Verify generated code has no syntax or compile errors
3. Verify every required script library is declared in package.json
4. Report validation results with detailed logs

Do not run functional browser tests in this gate. Always provide clear, structured validation reports."""

EXECUTOR_RUN_PROMPT = """Execute the following test scripts:

**Project Setup Commands**:
{setup_commands}

**Test Files**:
{test_files}

**Execution Command**: {execution_command}

Run the tests and report results in JSON format:
{{
    "status": "PASS|FAIL|ERROR",
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "execution_time": "...",
    "results": [
        {{
            "test_name": "...",
            "status": "PASS|FAIL|SKIP",
            "duration": "...",
            "error_message": "...",
            "stack_trace": "..."
        }}
    ],
    "logs": "..."
}}"""

AUTO_HEAL_PROMPT = """A test execution has failed. Analyze the error and generate a fix.

**Failed Test**: {test_name}
**Error Message**: {error_message}
**Stack Trace**: {stack_trace}
**Original Code**: 
```
{original_code}
```

**Auto-Heal Attempt**: {attempt_number} of 3

Analyze the root cause and provide:
1. Root cause analysis
2. Specific fix (minimal change needed)
3. Updated code

Output as JSON:
{{
    "root_cause": "...",
    "fix_description": "...",
    "updated_files": [
        {{
            "path": "...",
            "content": "..."
        }}
    ]
}}"""

COMMIT_PR_PROMPT = """Create a GitHub commit and pull request for the approved test scripts.

**Repository**: {target_repo}
**Branch**: {branch_name}
**Base Branch**: {base_branch}
**Files to commit**:
{files_list}

**PR Title**: {pr_title}
**PR Description**: 
{pr_description}

Use the GitHub MCP tools to:
1. Create a new branch from {base_branch}
2. Commit all test files
3. Create a pull request against {base_branch} with the above details"""
