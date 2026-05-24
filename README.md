# 🧪 Agentic QE — STLC Lifecycle Platform

End-to-end agentic Quality Engineering platform that automates the full Software Testing Life Cycle with **Human-in-the-Loop (HITL)** governance at every stage.

## 🏗️ Architecture

```
Jira/ADO → Requirement Analyser → [HITL] → Test Case Generator → [HITL] → Script Generator → [HITL] → Test Executor → GitHub PR
```

### Four Workflows

| Workflow | Agent | HITL Gate | Output |
|----------|-------|-----------|--------|
| **1. Requirements** | Requirement Analyser | ✅ Approve / ❌ Reject / 🔄 Regenerate | Testability analysis |
| **2. Test Cases** | Test Case Generator | ✅ Approve / ❌ Reject / 🔄 Regenerate | Detailed test cases |
| **3. Scripts** | Script Generator | ✅ Approve / ❌ Reject / 🔄 Regenerate | Playwright-BDD scripts |
| **4. Execution** | Test Executor | Auto-heal (3 attempts) | Execution results + PR |

## 🛠️ Tech Stack

- **LLM**: Groq (Llama 3.3 70B) via LangChain
- **Orchestration**: LangGraph with HITL interrupts
- **Vector Store**: ChromaDB + HuggingFace embeddings (local, free)
- **Test Framework**: Playwright-BDD (Node.js, TypeScript)
- **UI**: React + FastAPI
- **Integrations**: Jira API, Playwright MCP, GitHub MCP

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ (for Playwright)
- Git

### 2. Setup

```bash
# Clone and navigate
cd Agentic-E2E-Lifecycle

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys
```

### 3. Required API Keys

| Key | Where to get it |
|-----|----------------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| `JIRA_API_TOKEN` | Atlassian Account → Security → API Tokens |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub → Settings → Developer Settings → PATs |

### 4. Run

```bash
# Terminal 1: API
uvicorn ui.api:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: React UI
cd ui/react
npm install
npm run dev
```

Open http://127.0.0.1:5173 in your browser.

## 📁 Project Structure

```
├── agents/              # AI agents for each workflow
├── config/              # Settings and prompt templates
├── graph/               # LangGraph workflow engine
├── integrations/        # Jira, Playwright MCP, GitHub MCP
├── models/              # Pydantic data models
├── ui/                  # FastAPI API and React dashboard
├── vectorstore/         # ChromaDB + embeddings
└── utils/               # Logger and helpers
```

## 🎮 Demo Mode

The UI includes a **Demo Mode** that works without a Jira connection. Click "Load Sample Requirement" to test the full workflow with a sample login requirement.

## 📄 License

MIT
