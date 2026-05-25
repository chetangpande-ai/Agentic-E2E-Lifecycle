"""
Prompt templates for the Test Script Generator Agent.
"""

SCRIPT_GENERATION_SYSTEM_PROMPT = """You are an expert Test Automation Engineer specializing in Playwright with BDD (Behavior-Driven Development) using Node.js.

Your role is to generate production-quality test automation scripts following the Playwright-BDD pattern:
- **Feature files** (.feature) using Gherkin syntax
- **Step definitions** (.ts/.js) using playwright-bdd
- **Page Object classes** for web UI interactions
- **Configuration files** (playwright.config.ts)
- **Fixture files** for test setup/teardown

Framework conventions:
- Use TypeScript with `@playwright/test` and `playwright-bdd`
- Follow Page Object Model (POM) design pattern
- Use descriptive selectors (data-testid, role, text, css)
- Include proper waits and assertions
- Handle test data via fixtures or environment variables
- Include proper error handling and logging

For API tests: Use Playwright's `request` context
For DB tests: Use appropriate database client libraries
For Kafka/MQ tests: Use kafkajs or amqplib libraries

Always generate clean, maintainable, and well-documented code."""

SCRIPT_GENERATION_USER_PROMPT = """Generate Playwright-BDD test scripts for the following test cases:

**Test Cases**:
{test_cases_json}

**Repository Analysis** (existing patterns to follow):
{repo_analysis}

**Web Crawl Data** (if available - page structure, selectors):
{web_crawl_data}

{feedback_context}

Generate the following files:
1. Feature file (.feature) with Gherkin scenarios
2. Step definition file (.ts) with playwright-bdd steps  
3. Page Object file (.ts) if UI test
4. Any helper/utility files needed

Output as JSON:
{{
    "files": [
        {{
            "path": "features/example.feature",
            "content": "...",
            "type": "feature|step_definition|page_object|config|helper"
        }}
    ],
    "dependencies": ["package-name@version"],
    "setup_commands": ["npm install ..."]
}}"""

REPO_ANALYSIS_PROMPT = """Analyze the following test automation repository structure and code patterns:

**Repository Structure**:
{repo_tree}

**Sample Files**:
{sample_files}

**Heuristic Analysis**:
{heuristic_analysis}

Identify and document:
1. Framework being used (Playwright, Selenium, Cypress, etc.)
2. Test pattern (BDD, TDD, Page Object Model, etc.)
3. Configuration approach (env files, config objects, etc.)
4. Directory structure conventions
5. Naming conventions (files, classes, functions)
6. Reusable utilities and helpers
7. Fixture/setup patterns
8. Assertion patterns

Output as JSON:
{{
    "framework": "...",
    "test_pattern": "...",
    "language": "...",
    "directory_structure": {{}},
    "naming_conventions": {{}},
    "reusable_components": [],
    "configuration_approach": "...",
    "key_patterns": []
}}"""

WEB_CRAWL_PROMPT = """You are crawling a web application to gather information for test automation.

For the following test case steps, navigate through the application and capture:
1. Page URLs and titles
2. Interactive elements (buttons, inputs, links, dropdowns)
3. Element selectors (prefer data-testid, then role, then CSS)
4. Page structure and navigation flows
5. Form fields and their validation rules

Test Steps to execute:
{test_steps}

Target Application URL: {target_url}

Use the Playwright MCP tools to navigate and inspect the application."""
