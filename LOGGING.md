# Logging & Debugging Guide

## Overview

The Agentic E2E Lifecycle project includes comprehensive logging for debugging, analysis, and auditing all operations. Logs are written to both **console** (with rich formatting) and **files** (for analysis and persistence).

---

## Log Locations

All logs are stored in the `logs/` directory at the project root:

```
logs/
├── agentic_qe_20260523.log          # Main application log
├── requirement_analyser_20260523.log # Requirement analysis module
├── testcase_generator_20260523.log   # Test case generation module
├── script_generator_20260523.log     # Script generation module
├── test_executor_20260523.log        # Test execution module
├── jira_client_20260523.log          # Jira integration logs
├── github_mcp_20260523.log           # GitHub integration logs
└── workflow_20260523.log             # Workflow orchestration logs
```

**Log File Format**: `{module_name}_{YYYYMMDD}.log`
- New files are created daily
- Logs are appended to existing files (not overwritten)

---

## Log Configuration

Log level is controlled by the `LOG_LEVEL` environment variable in `.env`:

```dotenv
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (verbose)
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical error messages

---

## What Gets Logged

### 1. **Requirement Analyzer** (`requirement_analyser_YYYYMMDD.log`)

```
[START] RequirementAnalyser(KAN-5)
  - Requirement ID: KAN-5
  - Requirement Title: User Management CRUD Operations
  - Analysis Status: In Progress

[DEBUG] RequirementAnalysis - Data: {
  'req_id': 'KAN-5',
  'testability': 'HIGH',
  'test_cases_est': 38,
  'gaps_count': 2
}

[END] RequirementAnalyser(KAN-5) - Status: SUCCESS | Duration: 12.34s
```

**Logged Information**:
- Requirement ID and title
- Analysis start/end times
- Testability scores
- Estimated test case count
- Acceptance criteria gaps
- Error details (if analysis fails)

### 2. **Test Case Generator** (`testcase_generator_YYYYMMDD.log`)

```
[START] TestCaseGenerator(KAN-5)
  - Test Case Count: 38
  - Generation Status: In Progress

[DEBUG] TestCaseGeneration - Data: {
  'req_id': 'KAN-5',
  'generated_count': 38,
  'positive_cases': 28,
  'negative_cases': 10
}

[END] TestCaseGenerator(KAN-5) - Status: SUCCESS | Duration: 8.56s
```

**Logged Information**:
- Number of test cases generated
- Test case breakdown (positive, negative, boundary)
- Generation duration
- Error details with context

### 3. **Script Generator** (`script_generator_YYYYMMDD.log`)

```
[START] ScriptGenerator(SC-001)
  - Test Cases Count: 38
  - Target Repository: chetangpande-ai/HdfcBank-Test-Automation

[DEBUG] RepoAnalysis - Data: {
  'repo': 'HdfcBank-Test-Automation',
  'patterns_found': 12,
  'framework': 'Playwright-BDD'
}

[END] ScriptGenerator(SC-001) - Status: SUCCESS | Duration: 15.23s
```

**Logged Information**:
- Script generation progress
- Repository pattern analysis
- Generated file count and types
- Dependency resolution
- Error details with line numbers

### 4. **Test Executor** (`test_executor_YYYYMMDD.log`)

```
[START] TestExecutor(EX-001)
  - Script ID: SC-001
  - Test Count: 38

[DEBUG] TestExecution - Data: {
  'script_id': 'SC-001',
  'passed': 36,
  'failed': 2,
  'duration': 125.45
}

[ERROR] TestExecutor(EX-001) - AutoHealAttempt 1/3
  - Failed Test: test_create_user_with_invalid_email
  - Auto-heal Status: HEALING
  - Context: {'line': 42, 'error': 'Selector not found'}

[END] TestExecutor(EX-001) - Status: SUCCESS | Duration: 185.32s
```

**Logged Information**:
- Test execution start/end
- Pass/fail counts
- Failed test details
- Auto-heal attempts (if enabled)
- Execution duration
- Detailed error messages

### 5. **Jira Client** (`jira_client_YYYYMMDD.log`)

```
[START] JiraClient.__init__ | url=https://chetangpande1.atlassian.net | project=KAN
JiraClient initialized for project KAN

[START] JiraClient.fetch_requirements | JQL: project = "KAN" AND issuetype = Story
Found 15 requirements

[DEBUG] JiraFetch - Data: {
  'issue_count': 15,
  'jql': 'project = "KAN" AND issuetype = Story',
  'duration': 2.45
}
```

**Logged Information**:
- Jira connection status
- JQL query executed
- Number of issues fetched
- Issue details (ID, title, priority)
- Connection errors

### 6. **GitHub Integration** (`github_mcp_YYYYMMDD.log`)

```
[START] GitHubClient.create_branch | target=chetangpande-ai/HdfcBank-Test-Automation | branch=test/SC-001
Branch created successfully

[START] GitHubClient.commit_and_push | branch=test/SC-001 | files=38
Committed 38 files with message: "Automated test scripts for KAN-5"

[START] GitHubClient.create_pull_request | target=chetangpande-ai/HdfcBank-Test-Automation
PR created: https://github.com/chetangpande-ai/HdfcBank-Test-Automation/pull/123
```

**Logged Information**:
- Branch creation/deletion
- Commit messages and file counts
- Push status
- Pull request creation/status
- API errors

### 7. **Workflow Orchestration** (`workflow_20260523.log`)

```
[START] Workflow(thread-uuid-12345)
🏗️ Building STLC workflow graph...

[DEBUG] WorkflowNode - Data: {
  'node': 'fetch_requirements',
  'input_state': {...},
  'duration': 5.23
}

[START] WorkflowEdge - route_after_requirement_hitl
Next step: GENERATE_TESTCASES (APPROVED)

✅ Workflow graph compiled successfully
```

**Logged Information**:
- Workflow initialization
- Node execution (start/end)
- State transitions
- Conditional routing decisions
- HITL feedback processing

---

## Accessing Logs

### Option 1: Real-time Console Output

When running the application, logs appear in the console with rich formatting (colors, timestamps, file paths).

### Option 2: View Log Files

```bash
# View the main application log
cat logs/agentic_qe_*.log

# View logs from a specific module
cat logs/requirement_analyser_*.log

# Follow logs in real-time (Linux/Mac)
tail -f logs/agentic_qe_*.log

# Search for errors
grep "ERROR" logs/*.log

# Search for a specific requirement
grep "KAN-5" logs/*.log
```

### Option 3: Analyze Logs Programmatically

```python
import json
from pathlib import Path

# Read latest logs
log_dir = Path("logs")
log_files = sorted(log_dir.glob("*.log"), reverse=True)

for log_file in log_files[:5]:  # Last 5 log files
    with open(log_file) as f:
        content = f.read()
        # Parse and analyze
        print(f"File: {log_file.name}")
        print(f"Size: {len(content)} bytes")
        print(f"Errors: {content.count('ERROR')}")
```

---

## Log Analysis & Debugging

### 1. **Finding Failures**

```bash
# Find all errors
grep "ERROR\|FAIL\|Exception" logs/*.log

# Find errors for a specific requirement
grep "KAN-5.*ERROR" logs/*.log
```

### 2. **Performance Analysis**

```bash
# Extract duration information
grep "Duration:" logs/*.log | head -20

# Find slow operations
grep "Duration: [^0-5]" logs/*.log  # Operations > 5 seconds
```

### 3. **Workflow Tracing**

```bash
# Trace a specific workflow execution
grep "thread-uuid-12345" logs/workflow_*.log

# See state transitions
grep "WorkflowEdge\|route_" logs/workflow_*.log
```

### 4. **API Call Audit**

```bash
# Audit all Jira API calls
grep "JiraClient\|JQL:" logs/jira_client_*.log

# Audit all GitHub operations
grep "GitHubClient\|create_pull_request" logs/github_mcp_*.log
```

---

## Structured Log Format

All file logs follow this format:

```
TIMESTAMP - MODULE_NAME - LOG_LEVEL - [FILENAME:LINE_NUMBER] - MESSAGE
```

Example:
```
2026-05-23 19:56:22 - requirement_analyser - INFO - [requirement_analyser.py:84] - Analysis complete: Testability=HIGH, Est. Test Cases=38
```

---

## Debug Mode

To enable debug-level logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or temporarily in code
from utils.logger import setup_logger
logger = setup_logger(log_level="DEBUG")
```

Debug logs include:
- Detailed data structures
- Variable values at each step
- API request/response details
- Internal state transitions

---

## Troubleshooting Common Issues

### Issue: Logs not appearing

**Solution**: 
- Check `LOG_LEVEL` in `.env`
- Ensure `logs/` directory exists (created automatically)
- Verify file permissions

### Issue: Log files growing too large

**Solution**:
- Archive old logs: `mv logs/agentic_qe_202605*.log archive/`
- Use log rotation (implement in future)
- Reduce `LOG_LEVEL` to WARNING

### Issue: Cannot find specific error

**Solution**:
```bash
# Use grep with context
grep -B5 -A5 "ERROR" logs/*.log

# Search with timestamps
grep "2026-05-23 19:5" logs/*.log
```

---

## Best Practices

1. **Check logs when tests fail** - Always review the test executor logs first
2. **Monitor during execution** - Use `tail -f` to watch real-time progress
3. **Archive old logs** - Keep logs directory manageable
4. **Search by workflow ID** - Use thread IDs to trace complete workflows
5. **Share logs for debugging** - Include relevant log excerpts in bug reports

---

## Log Retention Policy

- **Keep logs for**: 30 days (configurable)
- **Archive older logs**: Move to separate archive folder
- **Auto-cleanup** (future): Implement scheduled cleanup

---

## Integration with Monitoring Tools

Future enhancements:
- ELK Stack integration (Elasticsearch, Logstash, Kibana)
- Splunk integration
- CloudWatch integration for AWS deployments
- Datadog integration for observability

---

## References

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Rich Library](https://rich.readthedocs.io/)
- [Structured Logging Best Practices](https://www.splunk.com/en_us/blog/devops/structured-logging-best-practices.html)
