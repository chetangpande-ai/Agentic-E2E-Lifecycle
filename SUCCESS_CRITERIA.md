# Agent Success Criteria & Metrics

## Overview
Each agent in the E2E Lifecycle must meet specific success criteria before its output is considered ready for downstream consumption.

---

## 1. Requirement Analyzer Agent

**Purpose:** Parse, validate, and structure requirements into actionable specifications

**Input:** Raw requirement text (from issues, PRs, JIRA tickets, GitHub discussions)  
**Output:** Structured `Requirement` model with clear acceptance criteria

### Success Criteria
- [ ] **Completeness** - All key requirements are extracted
  - Must identify: feature description, acceptance criteria, edge cases
  - Must flag missing information (e.g., "Who is the user?", "What's the success metric?")

- [ ] **Clarity** - Requirements are unambiguous
  - Each criterion is testable (avoid vague language like "should work well")
  - Use specific measurable terms (e.g., "response time < 200ms")

- [ ] **Traceability** - Source is preserved
  - Link back to original issue/PR/ticket
  - Include context (e.g., GitHub issue #123, JIRA story key)

- [ ] **Structured Output** - Valid `Requirement` model
  - All required fields populated
  - No null/empty critical fields

### Validation Tests
```python
# Test: Can parse typical GitHub issue
# Test: Can identify incomplete requirements and flag them
# Test: Can extract acceptance criteria in standardized format
# Test: Can handle multi-paragraph requirements
```

---

## 2. Test Case Generator Agent

**Purpose:** Convert requirements into comprehensive test cases covering all scenarios

**Input:** Structured `Requirement` model  
**Output:** List of `TestCase` models (positive, negative, boundary)

### Success Criteria
- [ ] **Coverage** - Test cases cover the requirement completely
  - At least 1 positive case per requirement
  - At least 1 negative/error case per requirement
  - Boundary/edge cases identified and tested

- [ ] **Independence** - Each test case is autonomous
  - Can run in any order
  - No test depends on another test's output
  - Can be executed in parallel

- [ ] **Idempotency** - Can run same test case multiple times
  - Same input always produces consistent test logic
  - No side effects across runs
  - Cleanup is explicit

- [ ] **Naming Convention** - Clear, searchable names
  - Format: `test_<feature>_<scenario>` (e.g., `test_login_valid_credentials`)
  - Avoid: ambiguous names, unclear abbreviations

- [ ] **Structured Output** - Valid `TestCase` models
  - Setup, action, assertion clearly defined
  - Expected result is explicit (pass condition stated)

### Validation Tests
```python
# Test: Generates positive case for happy path
# Test: Generates negative cases for error scenarios
# Test: Identifies boundary conditions
# Test: Test names follow naming convention
# Test: Can handle requirement with multiple acceptance criteria
```

---

## 3. Script Generator Agent

**Purpose:** Convert test cases into executable automation scripts

**Input:** List of `TestCase` models  
**Output:** Executable scripts (Python, Playwright, etc.)

### Success Criteria
- [ ] **Executability** - Scripts run without manual intervention
  - No hardcoded paths or user-specific values
  - All dependencies are declared
  - Scripts are safe to run (no destructive ops without consent)

- [ ] **Error Handling** - Failures are caught and reported
  - Exceptions are caught with meaningful messages
  - Logs capture what happened and why it failed
  - Retry logic for transient failures (e.g., network timeouts)

- [ ] **Logging** - Full trace for debugging
  - Each step is logged (input, action, output)
  - Timestamp for performance analysis
  - Log level appropriate (debug, info, warning, error)

- [ ] **Assertions** - Clear pass/fail criteria
  - Each assertion maps to an acceptance criterion
  - Assertion messages are specific (not just "assert False")
  - Soft assertions (warn vs fail) used appropriately

- [ ] **Version Control Ready** - Script is auditable
  - Comments explain complex logic
  - No temporary debugging code
  - Follows project coding standards

### Validation Tests
```python
# Test: Generated script is syntactically valid
# Test: Script imports all required modules
# Test: Script logs key steps
# Test: Script has meaningful assertions
# Test: Can run script without manual setup
```

---

## 4. Test Executor Agent

**Purpose:** Execute scripts reliably and report results

**Input:** Executable scripts + execution context  
**Output:** `Execution` model with pass/fail/error status + logs

### Success Criteria
- [ ] **Reliability** - Execution is stable
  - Same script produces consistent results
  - Transient failures are retried (configurable)
  - Timeout handling is explicit

- [ ] **Result Accuracy** - Correctly reports pass/fail
  - Pass = script exited 0 + all assertions passed
  - Fail = assertion failed (with specific failure message)
  - Error = script crashed (with stack trace)

- [ ] **Detailed Reporting** - Full context for debugging
  - Execution time captured
  - Environment info logged (Python version, OS, etc.)
  - All stdout/stderr captured
  - Screenshot/artifact captures if applicable

- [ ] **Traceability** - Results link back to source
  - Test case ID preserved
  - Requirement ID preserved
  - Execution ID for reproducibility

- [ ] **Performance** - No unnecessary slowdown
  - Execution time is reasonable for test complexity
  - Logging doesn't bloat output
  - No polling or inefficient retries

### Validation Tests
```python
# Test: Executes passing script correctly
# Test: Catches failing assertion with error message
# Test: Catches script crash with traceback
# Test: Retries transient failures
# Test: Timeout kills hanging script
# Test: Logs are complete and searchable
```

---

## Integration Criteria

### Requirement → Testcase
- [ ] Every acceptance criterion in Requirement has >= 1 test case
- [ ] Test case names are searchable back to requirement
- [ ] No test cases for requirements that aren't stated

### Testcase → Script
- [ ] Every test case is translated to executable script
- [ ] Script assertion maps to test case expected result
- [ ] Setup/teardown are explicit

### Script → Execution
- [ ] Script executes without errors (or errors are expected)
- [ ] Result status matches actual behavior
- [ ] Logs are linked to original script

---

## Quality Gates

### Before Shipping a Change
1. **Does it pass its own success criteria?**
2. **Are edge cases covered?**
3. **Can downstream agents consume the output?**
4. **Is it simple and understandable?**
5. **Have I verified with real examples?**

### Before Running in Production
1. **Does the full E2E workflow pass?**
2. **Are failure modes handled?**
3. **Can we debug if something breaks?**
4. **Is the output version-controlled?**
5. **Do we have a rollback plan?**

---

## Metrics to Track

- **Requirement Completeness** - % of requirements with all fields populated
- **Test Coverage** - # of test cases / # of acceptance criteria
- **Script Success Rate** - % of generated scripts that execute without error
- **Execution Reliability** - % of test runs with consistent results
- **Mean Time to Debug** - How long to trace failure to root cause
- **Throughput** - Requirements processed per hour (end-to-end)

---

## Review Checklist

When reviewing agent output, ask:

- [ ] Does the output solve the stated problem?
- [ ] Are there any unnecessary assumptions?
- [ ] Can someone else understand this without additional context?
- [ ] Is this the minimal solution?
- [ ] Have I verified with real data?
- [ ] Does this create any side effects?
- [ ] Can this scale to 10X the current load?
