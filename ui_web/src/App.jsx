import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "./api";
import mysqlLogo from "./assets/mysql-logo.svg";
import mariadbLogo from "./assets/mariadb-logo.svg";

const SIDEBAR_TABS = ["chat", "config", "profiles", "agents", "observability"];
const APP_NAME = "MariaDB + MySQL Root-Cause Insight";
const SECRET_MASK = "********";
const SECRET_CONFIG_KEYS = new Set(["OPENAI_API_KEY", "DB_PASSWORD", "SKYSQL_API_KEY"]);
const AGENT_LABELS = {
  analyze_slow_queries: "Slow Query Analysis",
  analyze_running_queries: "Running Query Analysis",
  perform_incident_triage: "Incident Triage",
  check_replication_health: "Replication Health",
  execute_database_query: "Database Inspector",
  get_skysql_observability_snapshot: "MariaDB Cloud Observability Snapshot"
};
const STARTER_QUESTIONS = [
  "What can you help me with?",
  "Give me a DB health report.",
  "Analyze slow queries from the last hour.",
  "What queries are running right now?",
  "Check replication health and summarize risks."
];
const CONFIG_FIELDS = [
  { key: "OPENAI_API_KEY", label: "OpenAI API Key", optional: false },
  { key: "OPENAI_MODEL", label: "OpenAI Model", optional: true },
  { key: "DB_HOST", label: "DB Host", optional: false },
  { key: "DB_PORT", label: "DB Port", optional: false },
  { key: "DB_USER", label: "DB User", optional: false },
  { key: "DB_PASSWORD", label: "DB Password", optional: false },
  { key: "DB_DATABASE", label: "Default Database", optional: false },
  { key: "SKYSQL_API_KEY", label: "MariaDB Cloud API Key", optional: true },
  { key: "SKYSQL_SERVICE_ID", label: "MariaDB Cloud Service ID", optional: true },
  { key: "SKYSQL_LOG_API_URL", label: "MariaDB Cloud Log API URL", optional: true }
];

const DEFAULT_PROFILE_FORM = {
  name: "",
  host: "",
  port: 3306,
  user: "",
  password: "",
  database: ""
};

function isSecretConfigKey(key) {
  return SECRET_CONFIG_KEYS.has(key);
}

function extractNextStepsFromText(text) {
  const lines = text.split("\n").map((line) => line.trim());
  const steps = [];
  let capture = false;
  for (const line of lines) {
    const normalized = line.replace(/^#+\s*/, "").replace(/[*`]/g, "").toLowerCase();
    if (
      normalized.startsWith("next steps") ||
      normalized.startsWith("recommendations") ||
      normalized.startsWith("recommended actions")
    ) {
      capture = true;
      continue;
    }
    if (capture && line.startsWith("#")) {
      break;
    }
    if (capture) {
      const bullet = line.match(/^[-*]\s+(.+)$/) || line.match(/^\d+\.\s+(.+)$/);
      if (bullet) {
        steps.push(bullet[1].replace(/[*`]/g, "").trim());
      }
    }
  }
  return steps.slice(0, 10);
}

function buildErrorHelp(errorMessage) {
  const message = (errorMessage || "").toLowerCase();
  if (!message) {
    return null;
  }
  if (message.includes("openai api connectivity failed")) {
    return "OpenAI API connectivity issue (not database): check internet, VPN/proxy/firewall, then retry.";
  }
  if (message.includes("openai api authentication/usage failed")) {
    return "OpenAI auth/quota issue: verify OPENAI_API_KEY, model access, and account quota.";
  }
  if (message.includes("database connection failed")) {
    return "Database connection issue: verify DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_DATABASE and SSL settings.";
  }
  if (message.includes("cannot reach backend api")) {
    return "UI cannot reach local API: make sure ./scripts/run_ui.sh is running.";
  }
  return null;
}

export function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [messages, setMessages] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState(localStorage.getItem("dba.sessionId") || null);
  const [configStatus, setConfigStatus] = useState(null);
  const [envValues, setEnvValues] = useState({});
  const [profilesState, setProfilesState] = useState({ active_profile_id: null, profiles: [] });
  const [newProfile, setNewProfile] = useState(DEFAULT_PROFILE_FORM);
  const [toggles, setToggles] = useState({});
  const [observability, setObservability] = useState({ summary: {}, recent_runs: [] });
  const [sessionsList, setSessionsList] = useState([]);
  const [nextSteps, setNextSteps] = useState([]);
  const [lastResponseMetrics, setLastResponseMetrics] = useState(null);
  const [runProgress, setRunProgress] = useState([]);
  const [apiConnected, setApiConnected] = useState(false);
  const [isLoadingBootstrap, setIsLoadingBootstrap] = useState(false);
  const [showStarterQuestions, setShowStarterQuestions] = useState(false);
  const [showInsights, setShowInsights] = useState(false);
  const chatEndRef = useRef(null);

  const latestRun = useMemo(() => observability.recent_runs.at(-1), [observability]);
  const errorHelp = useMemo(() => buildErrorHelp(error), [error]);
  const latestProgressMessage = useMemo(() => {
    if (!isRunning) {
      return "";
    }
    const latest = runProgress.length > 0 ? runProgress[runProgress.length - 1] : null;
    return latest?.message || "Starting analysis...";
  }, [isRunning, runProgress]);

  async function refreshAll(sessionOverride = undefined) {
    setIsLoadingBootstrap(true);
    const [status, envData, profiles, toggleData, summary, sessions] = await Promise.all([
      api.getConfigStatus(),
      api.getEnvValues(),
      api.getProfiles(),
      api.getToggles(),
      api.getObservability(),
      api.getSessions()
    ]);
    setConfigStatus(status);
    setEnvValues(envData.values || {});
    setProfilesState(profiles);
    setToggles(toggleData.toggles || {});
    setObservability(summary);
    setSessionsList(sessions.sessions || []);
    const activeSessionId = sessionOverride !== undefined ? sessionOverride : sessionId;
    if (activeSessionId) {
      const match = sessions.sessions.find((item) => item.id === activeSessionId);
      if (match) {
        setMessages(match.messages);
      } else {
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
    setApiConnected(true);
    setError("");
    setIsLoadingBootstrap(false);
  }

  useEffect(() => {
    refreshAll().catch((err) => {
      setApiConnected(false);
      setError(err.message);
      setIsLoadingBootstrap(false);
    });
  }, []);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("dba.sessionId", sessionId);
    }
  }, [sessionId]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, isRunning]);

  async function sendMessage(messageText) {
    const trimmed = messageText.trim();
    if (!trimmed || isRunning) {
      return;
    }

    const userMessage = {
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsRunning(true);
    setError("");

    try {
      const runStart = await api.startChatRun({
        message: trimmed,
        max_turns: 30,
        session_id: sessionId,
        profile_id: profilesState.active_profile_id
      });
      const runId = runStart.run_id;

      let runState = null;
      for (let attempt = 0; attempt < 240; attempt += 1) {
        runState = await api.getChatRun(runId);
        setRunProgress(runState.events || []);
        if (runState.status === "completed" || runState.status === "failed") {
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, 600));
      }

      if (!runState || runState.status !== "completed" || !runState.result) {
        const detail = runState?.error || "Run did not complete successfully.";
        throw new Error(detail);
      }

      const response = runState.result;
      const assistantMessage = {
        role: "assistant",
        content: response.response,
        created_at: response.created_at
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setSessionId(response.session_id);
      setLastResponseMetrics(response.metrics || null);
      const extractedSteps =
        response.next_steps && response.next_steps.length > 0
          ? response.next_steps
          : extractNextStepsFromText(response.response || "");
      setNextSteps(extractedSteps);
      await refreshAll(response.session_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
      setRunProgress([]);
    }
  }

  async function handleSend(messageText) {
    await sendMessage(messageText);
  }

  async function handleStarterQuestion(question) {
    await sendMessage(question);
  }

  async function saveEnvValues() {
    const payload = { ...envValues };
    for (const key of SECRET_CONFIG_KEYS) {
      const value = payload[key];
      if (value === SECRET_MASK || value === "") {
        delete payload[key];
      }
    }
    await api.updateEnv(payload);
    await refreshAll();
  }

  async function createProfile() {
    await api.createProfile({
      ...newProfile,
      port: Number(newProfile.port)
    });
    setNewProfile(DEFAULT_PROFILE_FORM);
    await refreshAll();
  }

  async function activateProfile(profileId) {
    await api.activateProfile(profileId);
    await refreshAll();
  }

  async function removeProfile(profileId) {
    await api.deleteProfile(profileId);
    await refreshAll();
  }

  async function updateToggles(key, value) {
    const payload = { ...toggles, [key]: value };
    setToggles(payload);
    await api.setToggles(payload);
    await refreshAll();
  }

  async function resetToggles() {
    const response = await api.setDefaultToggles();
    setToggles(response.toggles);
    await refreshAll();
  }

  async function startNewChat() {
    setSessionId(null);
    setMessages([]);
    setNextSteps([]);
    setLastResponseMetrics(null);
    localStorage.removeItem("dba.sessionId");
    await refreshAll(null);
  }

  async function clearCurrentChat() {
    if (!sessionId) {
      setMessages([]);
      setNextSteps([]);
      setLastResponseMetrics(null);
      return;
    }
    await api.deleteSession(sessionId);
    await startNewChat();
  }

  async function deleteSessionById(targetSessionId) {
    await api.deleteSession(targetSessionId);
    if (sessionId === targetSessionId) {
      await startNewChat();
      return;
    }
    await refreshAll(sessionId);
  }

  async function selectSession(nextSessionId) {
    setSessionId(nextSessionId);
    setNextSteps([]);
    setLastResponseMetrics(null);
    await refreshAll(nextSessionId);
  }

  return (
    <div className="app-root">
      <header className="top-banner">
        <div className="top-banner-title">
          <h1>{APP_NAME}</h1>
          <p>
            Go beyond surface metrics—trace problems to real causes, validate with evidence, and get
            actionable next steps for performance, health, and incidents.
          </p>
        </div>
        <div className="logo-strip">
          <img src={mysqlLogo} alt="MySQL logo" />
          <img src={mariadbLogo} alt="MariaDB logo" />
        </div>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <h2>Workspace</h2>
          <p className="subtitle">Switch views for chat, config, agents, and observability.</p>
          {SIDEBAR_TABS.map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? "nav-button active" : "nav-button"}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </aside>

        <main className="main">
        {!apiConnected && (
          <div className="warning">
            Backend not connected. Start it with <code>./scripts/run_ui.sh</code> (or run the API separately), then click retry.
            <div className="row-gap" style={{ marginTop: 8 }}>
              <button
                onClick={() =>
                  refreshAll().catch((err) => {
                    setApiConnected(false);
                    setError(err.message);
                    setIsLoadingBootstrap(false);
                  })
                }
              >
                Retry Connection
              </button>
            </div>
          </div>
        )}
        {error && (
          <div className="error">
            <div>{error}</div>
            {errorHelp && <div className="error-help">{errorHelp}</div>}
          </div>
        )}
        {isLoadingBootstrap && <div className="info">Loading configuration and history...</div>}

        {activeTab === "chat" && (
          <section className={showInsights ? "chat-layout with-insights" : "chat-layout"}>
            <div className="panel">
              <div className="chat-header">
                <h3>Chat</h3>
                <div className="row-gap">
                  <button onClick={() => setShowInsights((prev) => !prev)}>
                    {showInsights ? "Hide Insights" : "Show Insights"}
                  </button>
                  <button onClick={startNewChat}>Start New Chat</button>
                  <button className="danger" onClick={clearCurrentChat}>
                    Clear Current Chat
                  </button>
                </div>
              </div>
              <div className="session-tabs">
                <button
                  className={!sessionId ? "session-tab active" : "session-tab"}
                  onClick={startNewChat}
                >
                  New Chat
                </button>
                {sessionsList.slice(-8).reverse().map((session) => (
                  <div
                    key={session.id}
                    className={sessionId === session.id ? "session-pill active" : "session-pill"}
                    title={session.title || session.id}
                  >
                    <button
                      className="session-pill-main"
                      onClick={() => selectSession(session.id)}
                    >
                      {(session.title || "Chat").slice(0, 22)}
                    </button>
                    <button
                      className="session-pill-delete"
                      onClick={() => deleteSessionById(session.id)}
                      aria-label={`Delete chat ${session.title || session.id}`}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              <div className="chat-window">
                {messages.map((message, idx) => (
                  <div className={`message ${message.role}`} key={`${message.created_at}-${idx}`}>
                    <div className="message-role">{message.role}</div>
                    <div className="markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {isRunning && <div className="message assistant">{latestProgressMessage}</div>}
                <div ref={chatEndRef} />
              </div>
              <div className="composer">
                <ChatComposer onSend={handleSend} disabled={isRunning} />
              </div>
              <div className="starter-questions">
                <button
                  className="subtle-button"
                  onClick={() => setShowStarterQuestions((prev) => !prev)}
                  disabled={isRunning}
                >
                  {showStarterQuestions ? "Hide quick prompts" : "Show quick prompts"}
                </button>
                <div className={showStarterQuestions ? "starter-panel visible" : "starter-panel"}>
                  <h4>Quick Prompts</h4>
                  <div className="chip-row">
                    {STARTER_QUESTIONS.map((question) => (
                      <button
                        key={question}
                        className="chip-button"
                        onClick={() => handleStarterQuestion(question)}
                        disabled={isRunning}
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="next-steps">
                <h4>Next Steps</h4>
                {nextSteps.length === 0 ? (
                  <p>No extracted steps yet.</p>
                ) : (
                  <ol>
                    {nextSteps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                )}
              </div>
            </div>

            {showInsights && (
              <aside className="panel side-panel">
                <h3>Observability</h3>
                <p className="helper-text">Right now + cumulative usage across runs.</p>
                <h4>Last Invocation</h4>
                {lastResponseMetrics ? (
                  <div className="status-grid single-col">
                    {Object.entries(lastResponseMetrics).map(([key, value]) => (
                      <div key={key} className="status good">
                        {key}: {typeof value === "number" ? value.toLocaleString() : String(value)}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>No invocation metrics yet.</p>
                )}
                <h4>Cumulative Totals</h4>
                <div className="status-grid single-col">
                  {Object.entries(observability.summary || {}).map(([key, value]) => (
                    <div key={key} className="status good">
                      {key}: {typeof value === "number" ? value.toLocaleString() : String(value)}
                    </div>
                  ))}
                </div>
                <h4>Recent Runs</h4>
                <div className="mini-runs">
                  {(observability.recent_runs || []).slice(-5).reverse().map((run) => (
                    <div key={run.run_id} className="mini-run">
                      <div>{new Date(run.created_at).toLocaleString()}</div>
                      <div>tokens: {(run.metrics?.total_tokens || 0).toLocaleString()}</div>
                      <div>round trips: {run.metrics?.total_round_trips || 0}</div>
                    </div>
                  ))}
                </div>
                {isRunning && (
                  <>
                    <h4>Live Progress</h4>
                    <div className="mini-runs">
                      {runProgress.length === 0 ? (
                        <div className="mini-run">Starting...</div>
                      ) : (
                        runProgress.slice(-8).map((item) => (
                          <div key={`${item.timestamp}-${item.message}`} className="mini-run">
                            <div>{new Date(item.timestamp).toLocaleTimeString()}</div>
                            <div>{item.message}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </>
                )}
              </aside>
            )}
          </section>
        )}

        {activeTab === "config" && (
          <section className="panel">
            <h3>Config</h3>
            <p className="helper-text">
              Loads from and saves to <code>mariadb_db_agents/.env</code>. Save creates a backup at{" "}
              <code>.env.bak</code>.
            </p>
            <p className="helper-text">
              Secret fields are masked. To change a secret, type a new value and save.
            </p>
            <p className="helper-text">
              Note: env variable names use <code>SKYSQL_*</code> for compatibility, but UI labels show{" "}
              <strong>MariaDB Cloud</strong>.
            </p>
            <div className="status-grid">
              {configStatus &&
                Object.entries(configStatus.required).map(([key, valid]) => (
                  <div key={key} className={valid ? "status good" : "status bad"}>
                    {key}: {valid ? "set" : "missing"}
                  </div>
                ))}
            </div>
            <h4>Required</h4>
            <div className="form-grid">
              {CONFIG_FIELDS.filter((field) => !field.optional).map((field) => (
                <label key={field.key}>
                  {field.label}
                  <input
                    type={isSecretConfigKey(field.key) ? "password" : "text"}
                    value={envValues[field.key] || ""}
                    onChange={(e) => setEnvValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <h4>Optional</h4>
            <div className="form-grid">
              {CONFIG_FIELDS.filter((field) => field.optional).map((field) => (
                <label key={field.key}>
                  {field.label}
                  <input
                    type={isSecretConfigKey(field.key) ? "password" : "text"}
                    value={envValues[field.key] || ""}
                    onChange={(e) => setEnvValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <button onClick={saveEnvValues}>Save .env values</button>
          </section>
        )}

        {activeTab === "profiles" && (
          <section className="panel">
            <h3>DB Profiles</h3>
            <p className="helper-text">
              Profiles are saved connection presets. Activate one to copy its DB values into <code>.env</code> quickly.
            </p>
            <div className="profiles-list">
              {profilesState.profiles.map((profile) => (
                <div key={profile.id} className="profile-item">
                  <div>
                    <strong>{profile.name}</strong> - {profile.user}@{profile.host}:{profile.port}/{profile.database}
                  </div>
                  <div className="row-gap">
                    <button onClick={() => activateProfile(profile.id)}>
                      {profilesState.active_profile_id === profile.id ? "Active" : "Set Active"}
                    </button>
                    <button className="danger" onClick={() => removeProfile(profile.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <h4>Create profile</h4>
            <div className="form-grid">
              {Object.keys(DEFAULT_PROFILE_FORM).map((key) => (
                <label key={key}>
                  {key}
                  <input
                    type={key === "password" ? "password" : "text"}
                    value={newProfile[key]}
                    onChange={(e) => setNewProfile((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <button onClick={createProfile}>Create profile</button>
          </section>
        )}

        {activeTab === "agents" && (
          <section className="panel">
            <h3>Agent Controls</h3>
            <p className="helper-text">Disable specialist tools you do not want Copilot to call.</p>
            <div className="toggle-list">
              {Object.entries(toggles).map(([key, value]) => (
                <label key={key} className="toggle-item">
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(e) => updateToggles(key, e.target.checked)}
                  />
                  <span>{AGENT_LABELS[key] || key}</span>
                </label>
              ))}
            </div>
            <button onClick={resetToggles}>Reset safe defaults</button>
          </section>
        )}

        {activeTab === "observability" && (
          <section className="panel">
            <h3>Token Consumption</h3>
            <div className="status-grid">
              {Object.entries(observability.summary || {}).map(([key, value]) => (
                <div key={key} className="status good">
                  {key}: {typeof value === "number" ? value.toLocaleString() : String(value)}
                </div>
              ))}
            </div>
            <h4>Latest Run Totals</h4>
            {latestRun ? (
              <pre className="code">{JSON.stringify(latestRun.metrics, null, 2)}</pre>
            ) : (
              <p>No run history yet.</p>
            )}
          </section>
        )}
        </main>
      </div>
    </div>
  );
}

function ChatComposer({ onSend, disabled }) {
  const [draft, setDraft] = useState("");

  async function submit() {
    const message = draft.trim();
    if (!message || disabled) {
      return;
    }
    await onSend(message);
    setDraft("");
  }

  return (
    <>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask: Is my database healthy?"
        rows={4}
      />
      <button onClick={submit} disabled={disabled}>
        Send
      </button>
    </>
  );
}

