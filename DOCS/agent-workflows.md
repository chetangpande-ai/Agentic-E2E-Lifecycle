# Agent Workflows

This document describes each agent-level workflow in the Agentic E2E Lifecycle project. The parent orchestration is documented separately in `DOCS/parent-workflow.md`.

## Overview

The system follows an STLC pipeline:

```text
Requirement source
-> Requirement Analyzer
-> Human review
-> Test Case Generator
-> Human review
-> Repository analysis and script generation
-> Human review
-> Test Executor validation
-> GitHub PR creation
```

Each agent has one primary responsibility and writes its output into `AgenticQEState`. Human-in-the-loop gates decide whether downstream agents can consume that output.

## Workflow 1: Requirement Analysis

### Agent

`agents/requirement_analyser.py`

### Purpose

Convert raw Jira requirements into a structured, testable analysis that downstream agents can use.

### Inputs

- `Requirement` model built from Jira fields.
- Optional human regeneration feedback from `state.requirement_feedback`.

### Outputs

Stored in `state.analyzed_requirements` as:

```json
{
  "requirement": { "...raw requirement..." },
  "analysis": { "...RequirementAnalysis..." }
}
```

The analysis is expected to include:

- testability score
- functional requirements
- non-functional requirements
- acceptance criteria gaps
- recommended test types
- risks and dependencies
- suggested clarifications
- edge cases
- summary

### Success Criteria

- Extracts measurable and testable requirements.
- Identifies ambiguity and missing acceptance criteria.
- Produces structured output suitable for test-case generation.
- Keeps original requirement context available for review.

### Failure Handling

If Jira fetch or analysis fails, the node records:

- `state.error`
- an error message in `state.messages`

The workflow should not silently move forward with missing analysis.

## Workflow 2: Test Case Generation

### Agent

`agents/testcase_generator.py`

### Purpose

Generate concise, high-value test cases from approved requirement analysis.

### Inputs

- Approved `Requirement`
- Approved `RequirementAnalysis`
- Optional human regeneration feedback from `state.testcase_feedback`

### Output

Stored in `state.generated_testcases` as serialized `TestCase` models.

Each test case includes:

- ID
- requirement ID
- title
- description
- preconditions
- test type
- priority
- numbered steps
- test data
- expected result
- tags

### Token Budget Behavior

The generator is intentionally compact to stay under the Groq `8000 TPM` limit:

- It asks for 4 to 5 highest-value test cases by default.
- Requirement text, acceptance criteria, edge cases, and feedback are truncated before the prompt is built.
- LLM output is capped with `max_tokens=1800`.

### Success Criteria

- Covers positive, negative, and boundary scenarios.
- Keeps tests independent and idempotent.
- Uses `TC_XXX` naming.
- Produces strict JSON parseable by `parse_json_from_llm`.

### Failure Handling

If parsing fails or no test cases are returned:

- the agent logs the raw response preview
- raises an error
- the node stores a clear message and avoids moving to the next step

## Workflow 3A: Repository Analysis and Ingestion

### Components

- `integrations/repository_ingestion.py`
- `integrations/repo_analyzer.py`
- `agents/repository_analysis_agent.py`
- `vectorstore/indexer.py`
- `vectorstore/store.py`

### Purpose

Analyze the latest `main` branch of the target repository and prepare reusable context for script generation.

### Source of Truth

Only `main` is analyzed. Other branches are ignored.

The ingestion service checks:

```text
git ls-remote --heads <repo-url> main
```

The cache key is:

```text
<repo_url>|main|<head_sha>
```

### Refresh Rules

If `main` SHA is unchanged:

- reuse cached repo profile from `chroma_db/repo_profiles.json`
- reuse existing vector store contents
- skip coding-agent repo analysis

If `main` SHA changed:

- clone `main`
- run heuristic repo analysis
- reset Chroma `code_patterns`
- index code chunks
- run coding-agent repo analysis
- save the new repo profile cache

If the target repo is empty or has no `main`:

- the workflow tries the reference repo
- if the reference repo is also empty, script generation uses defaults

### Heuristic Repo Analysis

`RepoAnalyzer` detects:

- framework
- language
- test pattern
- directory structure
- naming conventions
- reusable component paths
- configuration approach
- key patterns

It scans code files with these extensions:

```text
.ts, .js, .py, .java, .feature, .json
```

It skips hidden folders, `node_modules`, `__pycache__`, and virtual environment folders.

### Coding-Agent Repo Analysis

`RepositoryAnalysisAgent` receives:

- repo tree
- representative files
- heuristic analysis

It returns a refined `RepoAnalysis` profile. If the LLM fails, the system falls back to the heuristic analysis.

### Vector Store Ingestion

Code chunks are stored in Chroma collection:

```text
code_patterns
```

Feature files are stored as whole-file chunks. Code files are chunked around function/class-like boundaries or by size.

## Workflow 3B: Script Generation

### Agent

`agents/script_generator.py`

### Purpose

Generate Playwright-BDD test automation files from approved test cases and repository context.

### Inputs

- Approved test cases from `state.generated_testcases`
- Cached/refreshed `RepoAnalysis`
- Vector search results from `code_patterns`
- Optional web crawl data
- Optional human regeneration feedback from `state.script_feedback`

### Output

Stored in:

- `state.generated_scripts`
- `state.script_dependencies`
- `state.script_setup_commands`

Generated files normally include:

- `.feature` file
- step definition `.ts` file
- test data JSON fixture
- `playwright.config.ts`
- `package.json`
- `tsconfig.json`

### Token Budget Behavior

The script generator is capped to avoid Groq `8000 TPM` failures:

- max 5 test cases in prompt
- compact test-case summaries
- compact repo profile
- max 2 semantic-search queries
- top 1 vector result per query
- capped RAG context
- capped web-crawl and feedback text
- LLM output capped with `max_tokens=1800`

### Fallback Behavior

If the LLM returns no parseable files, the agent builds fallback Playwright-BDD files locally. The fallback files are executable and include required project config.

### Success Criteria

- Produces executable TypeScript Playwright-BDD assets.
- Includes dependencies required by imports.
- Includes project config for empty repositories.
- Follows repository conventions when repo analysis is available.

## Workflow 4: Test Executor Validation

### Agent

`agents/test_executor.py`

### Purpose

Validate generated scripts before PR creation.

The executor does not run browser functional tests. It performs repository readiness checks.

### Checks

1. Inspect target repo branches.
2. If `main` exists, clone/pull latest `main`.
3. If the repo is empty, validate in a blank workspace.
4. Write generated files.
5. Verify required packages are present in `package.json`.
6. Verify TypeScript/JavaScript/JSON compile or syntax state.

### Output

Stored in `state.execution_results` as an `ExecutionResult`.

The result has individual checks:

- `main_branch_sync`
- `package_json_dependencies`
- `syntax_compile`

### Success Criteria

- Existing repo code is based on latest `main`.
- Generated files do not introduce compile/syntax errors.
- Required libraries are represented in `package.json`.
- Failure details are traceable in logs and UI.

### Failure Handling

If validation fails:

- parent workflow routes back to script review
- PR creation is blocked in the UI

## Workflow 5: GitHub PR Creation

### Component

`integrations/github_pr.py`

### Purpose

Create a branch, commit generated files, and open a PR against `main`.

### Implementation

Uses GitHub REST API instead of local `git push`.

This avoids local Git credential manager issues on Windows.

### Empty Repo Behavior

If the repo has no branches:

- initialize `main` with `README.md`
- create generated branch from `main`
- upload generated files
- create PR against `main`

### Existing File Update Behavior

When a generated file already exists on the branch, GitHub requires the file SHA. The helper:

1. checks whether the file exists on the generated branch
2. supplies `sha` for updates
3. omits `sha` for new files

### Required GitHub Token Permissions

Fine-grained PAT needs:

- `Contents`: read and write
- `Pull requests`: read and write
- `Metadata`: read

### Success Criteria

- PR is created against `main`.
- Generated files are visible in the PR.
- Existing generated files can be updated without `sha wasn't supplied` errors.

## Human Review Gates

Human review gates exist after:

- requirement analysis
- test case generation
- script generation

Each gate supports:

- approve
- reject
- regenerate with feedback

Regeneration attempts are capped at 3 per stage in the graph routing layer.

## Logging and Observability

Logs are written under `logs/`.

The UI exposes a "Latest Log" panel backed by:

```text
GET /api/logs/latest
```

The endpoint prefers `agentic_qe_*.log` and returns a capped tail for quick analysis.
