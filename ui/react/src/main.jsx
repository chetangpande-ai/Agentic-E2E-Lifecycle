import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Check,
  CircleAlert,
  CircleX,
  Code2,
  FileText,
  FlaskConical,
  GitPullRequest,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Settings,
  TestTube2,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const steps = [
  { id: 0, label: "Requirements", icon: FileText },
  { id: 1, label: "Analysis", icon: Search },
  { id: 2, label: "Test Cases", icon: TestTube2 },
  { id: 3, label: "Scripts", icon: Code2 },
  { id: 4, label: "Execution", icon: Play },
  { id: 5, label: "PR", icon: GitPullRequest },
];

const emptyState = {
  workflow_step: 0,
  raw_requirements: [],
  analyzed_requirements: [],
  generated_testcases: [],
  generated_scripts: [],
  script_dependencies: [],
  script_setup_commands: [],
  execution_results: [],
  pr_url: "",
  rejected_step: -1,
  messages: [],
};

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Request failed: ${response.status}`);
  }
  return payload;
}

function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Panel({ title, children }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Sidebar({ config, onReset, busy }) {
  const configured = config?.configured || {};
  const connectionRows = [
    ["Jira", configured.jira, config?.jira_project_key || "Not configured"],
    ["LLM", configured.llm, config?.groq_model || "Not configured"],
    ["GitHub", configured.github, config?.github_target_repo || "Not configured"],
    ["Target App", configured.target_app, config?.target_app_url || "Not set"],
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <FlaskConical size={28} />
        <div>
          <h1>Agentic QE</h1>
          <p>STLC lifecycle platform</p>
        </div>
      </div>

      <div className="side-section">
        <h3>Connections</h3>
        {connectionRows.map(([name, ok, detail]) => (
          <div className="connection" key={name}>
            <span className={ok ? "dot dot-ok" : "dot dot-off"} />
            <div>
              <strong>{name}</strong>
              <small>{detail}</small>
            </div>
          </div>
        ))}
      </div>

      <details className="config-details">
        <summary>
          <Settings size={16} />
          Configuration
        </summary>
        <dl>
          <dt>Jira URL</dt>
          <dd>{config?.jira_url || "N/A"}</dd>
          <dt>Jira User</dt>
          <dd>{config?.jira_username || "N/A"}</dd>
          <dt>JQL</dt>
          <dd>{config?.jql_filter || "N/A"}</dd>
          <dt>Groq Key</dt>
          <dd>{config?.groq_api_key_masked || "N/A"}</dd>
          <dt>GitHub PAT</dt>
          <dd>{config?.github_pat_masked || "N/A"}</dd>
        </dl>
      </details>

      <button className="button secondary full" disabled={busy} onClick={onReset}>
        <RefreshCw size={16} />
        Reset Workflow
      </button>
    </aside>
  );
}

function WorkflowTracker({ currentStep, rejectedStep }) {
  return (
    <div className="tracker">
      {steps.map((step, index) => {
        const Icon = step.icon;
        const status =
          rejectedStep === step.id ? "rejected" : step.id < currentStep ? "done" : step.id === currentStep ? "active" : "pending";
        return (
          <React.Fragment key={step.id}>
            <div className="track-step">
              <div className={`track-icon ${status}`}>
                {status === "done" ? <Check size={19} /> : status === "rejected" ? <CircleX size={19} /> : <Icon size={19} />}
              </div>
              <span>{step.label}</span>
            </div>
            {index < steps.length - 1 && <div className={`connector ${step.id < currentStep ? "done" : ""}`} />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function ReviewActions({ onApprove, onReject, onRegenerate, busy }) {
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);

  return (
    <div className="review">
      <h3>Human Review</h3>
      <div className="actions">
        <button className="button primary" disabled={busy} onClick={onApprove}>
          <Check size={16} />
          Approve
        </button>
        <button className="button danger" disabled={busy} onClick={onReject}>
          <CircleX size={16} />
          Reject
        </button>
        <button className="button secondary" disabled={busy} onClick={() => setShowFeedback((value) => !value)}>
          <RefreshCw size={16} />
          Regenerate
        </button>
      </div>
      {showFeedback && (
        <div className="feedback">
          <textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Feedback for regeneration" />
          <button className="button primary" disabled={busy} onClick={() => onRegenerate(feedback)}>
            Submit Feedback
          </button>
        </div>
      )}
    </div>
  );
}

function RequirementsStep({ onFetch, onDemo, busy, config }) {
  const [ids, setIds] = useState("");
  return (
    <Panel title="Fetch Requirements">
      {!config?.configured?.jira && (
        <div className="notice warning">
          <CircleAlert size={18} />
          Jira is not configured. Use demo mode or update the .env file.
        </div>
      )}
      <div className="fetch-row">
        <input value={ids} onChange={(event) => setIds(event.target.value)} placeholder="PROJ-101, PROJ-102" />
        <button className="button primary" disabled={busy} onClick={() => onFetch(ids)}>
          <Search size={16} />
          Fetch and Analyze
        </button>
      </div>
      <div className="demo-band">
        <div>
          <strong>Demo mode</strong>
          <p>Load a sample login requirement without Jira. A Groq key is still needed for analysis.</p>
        </div>
        <button className="button secondary" disabled={busy} onClick={onDemo}>
          Load Sample Requirement
        </button>
      </div>
    </Panel>
  );
}

function RequirementAnalysis({ items, onApprove, onReject, onRegenerate, busy }) {
  return (
    <Panel title="Requirement Analysis Results">
      {items.map((item, index) => {
        const req = item.requirement || {};
        const analysis = item.analysis || {};
        return (
          <details className="item" key={req.id || index} open={index === 0}>
            <summary>
              <span>{req.id}</span>
              <strong>{req.title}</strong>
              <Badge tone={(analysis.testability_score || "medium").toLowerCase()}>{analysis.testability_score || "MEDIUM"}</Badge>
            </summary>
            <div className="two-col">
              <div>
                <p className="muted">{req.description}</p>
                <h4>Functional Requirements</h4>
                <ul>{(analysis.functional_requirements || []).map((value) => <li key={value}>{value}</li>)}</ul>
                <h4>Test Types</h4>
                <div className="tags">{(analysis.recommended_test_types || []).map((value) => <Badge key={value}>{value}</Badge>)}</div>
              </div>
              <div>
                <Metric label="Estimated Test Cases" value={analysis.estimated_test_cases_count || 0} />
                {(analysis.acceptance_criteria_gaps || []).map((gap) => (
                  <div className="notice warning" key={gap}>{gap}</div>
                ))}
                {(analysis.risks_and_dependencies || []).map((risk) => (
                  <div className="notice danger" key={risk}>{risk}</div>
                ))}
              </div>
            </div>
            {analysis.summary && <p className="summary">{analysis.summary}</p>}
          </details>
        );
      })}
      <ReviewActions busy={busy} onApprove={onApprove} onReject={onReject} onRegenerate={onRegenerate} />
    </Panel>
  );
}

function TestCases({ testcases, onGenerate, onApprove, onReject, onRegenerate, busy }) {
  const counts = useMemo(() => {
    const ui = testcases.filter((tc) => tc.test_type === "UI").length;
    const apiCount = testcases.filter((tc) => tc.test_type === "API").length;
    return { ui, api: apiCount, other: testcases.length - ui - apiCount };
  }, [testcases]);

  if (!testcases.length) {
    return (
      <Panel title="Generate Test Cases">
        <p className="muted">Approved requirements are ready for test case generation.</p>
        <button className="button primary" disabled={busy} onClick={() => onGenerate("")}>
          <RefreshCw size={16} />
          Generate Test Cases
        </button>
      </Panel>
    );
  }

  return (
    <Panel title={`Generated Test Cases (${testcases.length})`}>
      <div className="metrics">
        <Metric label="Total" value={testcases.length} />
        <Metric label="UI Tests" value={counts.ui} />
        <Metric label="API Tests" value={counts.api} />
        <Metric label="Other" value={counts.other} />
      </div>
      {testcases.map((tc) => (
        <details className="item" key={tc.id}>
          <summary>
            <span>{tc.id}</span>
            <strong>{tc.title}</strong>
            <Badge tone={(tc.priority || "p2").toLowerCase()}>{tc.priority}</Badge>
            <Badge tone={(tc.test_type || "ui").toLowerCase()}>{tc.test_type}</Badge>
          </summary>
          <p className="muted">{tc.description}</p>
          {!!tc.preconditions?.length && (
            <>
              <h4>Preconditions</h4>
              <ul>{tc.preconditions.map((value) => <li key={value}>{value}</li>)}</ul>
            </>
          )}
          <h4>Test Steps</h4>
          <ol>
            {(tc.steps || []).map((step) => (
              <li key={`${tc.id}-${step.step_number}`}>
                <strong>{step.action}</strong>
                <span>Input: {step.input_data || "-"}</span>
                <span>Expected: {step.expected_result || "-"}</span>
              </li>
            ))}
          </ol>
        </details>
      ))}
      <ReviewActions busy={busy} onApprove={onApprove} onReject={onReject} onRegenerate={onRegenerate} />
    </Panel>
  );
}

function Scripts({ scripts, dependencies, setupCommands, onGenerate, onApprove, onReject, onRegenerate, busy }) {
  const [activePath, setActivePath] = useState("");
  const activeScript = scripts.find((script) => script.path === activePath) || scripts[0];

  useEffect(() => {
    if (scripts.length && !scripts.some((script) => script.path === activePath)) {
      setActivePath(scripts[0].path);
    }
  }, [activePath, scripts]);

  if (!scripts.length) {
    return (
      <Panel title="Generate Scripts">
        <p className="muted">Approved test cases are ready for Playwright-BDD script generation.</p>
        <button className="button primary" disabled={busy} onClick={() => onGenerate("")}>
          <Code2 size={16} />
          Generate Scripts
        </button>
      </Panel>
    );
  }

  return (
    <Panel title={`Generated Test Scripts (${scripts.length} files)`}>
      <div className="file-list">
        {scripts.map((script) => (
          <button className={script.path === activeScript?.path ? "selected" : ""} key={script.path} onClick={() => setActivePath(script.path)}>
            {script.path}
          </button>
        ))}
      </div>
      {!!dependencies.length && <div className="tags">{dependencies.map((dep) => <Badge key={dep}>{dep}</Badge>)}</div>}
      {!!setupCommands.length && (
        <div className="setup">
          {setupCommands.map((command) => <code key={command}>{command}</code>)}
        </div>
      )}
      {activeScript && <pre className="code"><code>{activeScript.content}</code></pre>}
      <ReviewActions busy={busy} onApprove={onApprove} onReject={onReject} onRegenerate={onRegenerate} />
    </Panel>
  );
}

function Execution({ results, prUrl, onRun, onCommit, busy }) {
  if (!results.length) {
    return (
      <Panel title="Test Execution">
        <p className="muted">Approved scripts are ready to execute with auto-heal.</p>
        <button className="button primary" disabled={busy} onClick={onRun}>
          <Play size={16} />
          Execute Tests
        </button>
      </Panel>
    );
  }

  const result = results[0];
  return (
    <Panel title="Test Execution Results">
      <div className="status-line">
        <Badge tone={(result.status || "error").toLowerCase()}>{result.status}</Badge>
        {prUrl && <a href={prUrl}>{prUrl}</a>}
      </div>
      <div className="metrics">
        <Metric label="Total Tests" value={result.total_tests || 0} />
        <Metric label="Passed" value={result.passed || 0} />
        <Metric label="Failed" value={result.failed || 0} />
        <Metric label="Auto-Heal Attempts" value={result.auto_heal_attempts?.length || 0} />
      </div>
      {(result.results || []).map((test) => (
        <details className="item" key={test.test_name}>
          <summary>
            <strong>{test.test_name}</strong>
            <Badge tone={(test.status || "error").toLowerCase()}>{test.status}</Badge>
          </summary>
          {test.error_message && <div className="notice danger">{test.error_message}</div>}
          {test.stack_trace && <pre className="code"><code>{test.stack_trace}</code></pre>}
        </details>
      ))}
      {result.logs && <pre className="code"><code>{result.logs}</code></pre>}
      {!prUrl && (
        <button className="button primary" disabled={busy} onClick={onCommit}>
          <GitPullRequest size={16} />
          Commit to GitHub and Create PR
        </button>
      )}
    </Panel>
  );
}

function App() {
  const [state, setState] = useState(emptyState);
  const [config, setConfig] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(label, callback) {
    setBusy(true);
    setError("");
    try {
      const nextState = await callback();
      setState(nextState);
    } catch (err) {
      setError(`${label}: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    Promise.all([api("/api/state"), api("/api/config")])
      .then(([nextState, nextConfig]) => {
        setState(nextState);
        setConfig(nextConfig);
      })
      .catch((err) => setError(err.message));
  }, []);

  const actions = {
    reset: () => run("Reset failed", () => api("/api/reset", { method: "POST" })),
    fetchRequirements: (ids) => run("Fetch failed", () => api("/api/requirements/fetch", { method: "POST", body: JSON.stringify({ requirement_ids: ids }) })),
    demo: () => run("Demo load failed", () => api("/api/demo/load", { method: "POST" })),
    approveRequirements: () => run("Approval failed", () => api("/api/requirements/approve", { method: "POST" })),
    rejectRequirements: () => run("Reject failed", () => api("/api/requirements/reject", { method: "POST" })),
    regenerateRequirements: (feedback) => run("Regenerate failed", () => api("/api/requirements/regenerate", { method: "POST", body: JSON.stringify({ feedback }) })),
    generateTestcases: (feedback = "") => run("Test case generation failed", () => api("/api/testcases/generate", { method: "POST", body: JSON.stringify({ feedback }) })),
    approveTestcases: () => run("Approval failed", () => api("/api/testcases/approve", { method: "POST" })),
    rejectTestcases: () => run("Reject failed", () => api("/api/testcases/reject", { method: "POST" })),
    generateScripts: (feedback = "") => run("Script generation failed", () => api("/api/scripts/generate", { method: "POST", body: JSON.stringify({ feedback }) })),
    approveScripts: () => run("Approval failed", () => api("/api/scripts/approve", { method: "POST" })),
    rejectScripts: () => run("Reject failed", () => api("/api/scripts/reject", { method: "POST" })),
    runExecution: () => run("Execution failed", () => api("/api/execution/run", { method: "POST" })),
    commitPr: () => run("PR creation failed", () => api("/api/commit-pr", { method: "POST" })),
  };

  let main;
  if (state.rejected_step >= 0) {
    main = <div className="notice danger large">Workflow was rejected at review stage {state.rejected_step}. Reset the workflow to start over.</div>;
  } else if (state.workflow_step === 0) {
    main = <RequirementsStep busy={busy} config={config} onFetch={actions.fetchRequirements} onDemo={actions.demo} />;
  } else if (state.workflow_step === 1) {
    main = (
      <RequirementAnalysis
        items={state.analyzed_requirements}
        busy={busy}
        onApprove={actions.approveRequirements}
        onReject={actions.rejectRequirements}
        onRegenerate={actions.regenerateRequirements}
      />
    );
  } else if (state.workflow_step === 2) {
    main = (
      <TestCases
        testcases={state.generated_testcases}
        busy={busy}
        onGenerate={actions.generateTestcases}
        onApprove={actions.approveTestcases}
        onReject={actions.rejectTestcases}
        onRegenerate={actions.generateTestcases}
      />
    );
  } else if (state.workflow_step === 3) {
    main = (
      <Scripts
        scripts={state.generated_scripts}
        dependencies={state.script_dependencies}
        setupCommands={state.script_setup_commands}
        busy={busy}
        onGenerate={actions.generateScripts}
        onApprove={actions.approveScripts}
        onReject={actions.rejectScripts}
        onRegenerate={actions.generateScripts}
      />
    );
  } else if (state.workflow_step === 4) {
    main = <Execution results={state.execution_results} prUrl={state.pr_url} busy={busy} onRun={actions.runExecution} onCommit={actions.commitPr} />;
  } else {
    main = <div className="notice success large">Workflow complete. All tests have been generated, executed, and committed.</div>;
  }

  return (
    <div className="app">
      <Sidebar config={config} busy={busy} onReset={actions.reset} />
      <main>
        <header className="hero">
          <div>
            <h1>Agentic QE - STLC Lifecycle</h1>
            <p>End-to-end test lifecycle automation with AI agents and human review gates.</p>
          </div>
          {busy && (
            <div className="busy">
              <Loader2 size={18} className="spin" />
              Working
            </div>
          )}
        </header>
        <WorkflowTracker currentStep={state.workflow_step} rejectedStep={state.rejected_step} />
        {error && <div className="notice danger">{error}</div>}
        {!!state.messages?.length && (
          <details className="log">
            <summary>Workflow Log</summary>
            <ul>{state.messages.slice(-10).map((message, index) => <li key={`${message}-${index}`}>{message}</li>)}</ul>
          </details>
        )}
        {main}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
