"""Connectivity test script for all integrations."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("CONNECTIVITY TEST")
print("=" * 60)

failures = []

# 1. Test Groq LLM
print("\n[1/3] Testing Groq LLM...")
try:
    from langchain_groq import ChatGroq
    llm = ChatGroq(
        model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.1,
        api_key=os.environ.get("GROQ_API_KEY", ""),
        max_tokens=20,
    )
    resp = llm.invoke("Say hello in one word")
    print(f"  OK - Model: {os.environ.get('GROQ_MODEL')}")
    print(f"  Response: {resp.content[:80]}")
except Exception as e:
    print(f"  FAIL - {str(e)[:200]}")
    failures.append("Groq LLM")

# 2. Test Jira
print("\n[2/3] Testing Jira...")
try:
    from atlassian import Jira
    jira = Jira(
        url=os.environ.get("JIRA_URL", ""),
        username=os.environ.get("JIRA_USERNAME", ""),
        password=os.environ.get("JIRA_API_TOKEN", ""),
        cloud=True,
    )
    project_key = os.environ.get("JIRA_PROJECT_KEY", "KAN")
    jql = 'project = "' + project_key + '" AND ' + os.environ.get("JIRA_JQL_FILTER", "issuetype = Story")
    result = jira.jql(jql, limit=5)
    issues = result.get("issues", [])
    print(f"  OK - Found {len(issues)} issues in project {project_key}")
    for issue in issues[:5]:
        print(f"    {issue['key']}: {issue['fields']['summary']}")
except Exception as e:
    print(f"  FAIL - {str(e)[:300]}")
    failures.append("Jira")

# 3. Test GitHub
print("\n[3/3] Testing GitHub...")
try:
    import httpx
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    target = os.environ.get("GITHUB_TARGET_REPO", "")
    ref = os.environ.get("GITHUB_REFERENCE_REPO", "")

    r1 = httpx.get(f"https://api.github.com/repos/{target}", headers=headers)
    status1 = "OK" if r1.status_code == 200 else f"FAIL ({r1.status_code})"
    print(f"  Target Repo: {target} - {status1}")
    if r1.status_code != 200:
        failures.append("GitHub target repo")

    r2 = httpx.get(f"https://api.github.com/repos/{ref}", headers=headers)
    status2 = "OK" if r2.status_code == 200 else f"FAIL ({r2.status_code})"
    print(f"  Reference Repo: {ref} - {status2}")
    if r2.status_code != 200:
        failures.append("GitHub reference repo")
except Exception as e:
    print(f"  FAIL - {str(e)[:200]}")
    failures.append("GitHub")

print("\n" + "=" * 60)
if failures:
    print(f"Connectivity test failed: {', '.join(failures)}")
else:
    print("All connectivity tests passed.")
print("=" * 60)

sys.exit(1 if failures else 0)
