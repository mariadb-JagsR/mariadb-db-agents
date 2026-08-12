import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "./api";
import { EvidenceTracePanel } from "./EvidenceTracePanel";
import mariadbLogo from "./assets/mariadb-logo.svg";

const SETTINGS_TABS = ["config", "profiles", "agents", "observability"];
const APP_NAME = "DBA Pulse";
const APP_TAGLINE = "Read-only · Evidence-backed · MariaDB / MySQL DBA assist";
const GITHUB_URL = "https://github.com/mariadb-JagsR/mariadb-db-agents";
const DOCS_URL = "https://github.com/mariadb-JagsR/mariadb-db-agents/tree/main/docs";
const APP_BANNER_SUBLINE =
  "Go beyond surface metrics—trace problems to real causes, validate with evidence, and get actionable next steps for performance, health, and incidents.";
const SECRET_MASK = "********";
const SECRET_CONFIG_KEYS = new Set(["OPENAI_API_KEY", "DB_PASSWORD", "MARIADB_CLOUD_API_KEY"]);
const AGENT_LABELS = {
  analyze_slow_queries: "Slow Query Analysis",
  analyze_running_queries: "Running Query Analysis",
  perform_incident_triage: "Incident Triage",
  check_replication_health: "Replication Health",
  execute_database_query: "Database Inspector",
  get_mariadb_cloud_observability_snapshot: "MariaDB Cloud Observability Snapshot",
  query_mariadb_cloud_observability_metrics: "MariaDB Cloud Metrics Query",
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
  { key: "MARIADB_CLOUD_API_KEY", label: "MariaDB Cloud API Key", optional: true },
  { key: "MARIADB_CLOUD_SERVICE_ID", label: "MariaDB Cloud Service ID", optional: true },
  { key: "MARIADB_CLOUD_LOG_API_URL", label: "MariaDB Cloud Log API URL", optional: true }
];

function SessionTitleButton({ title, onClick }) {
  const buttonRef = useRef(null);
  const [previewPosition, setPreviewPosition] = useState(null);

  function showPreview() {
    const button = buttonRef.current;
    if (!button || button.scrollWidth <= button.clientWidth) return;

    const rect = button.getBoundingClientRect();
    setPreviewPosition({
      left: rect.right + 10,
      top: Math.min(rect.top, window.innerHeight - 120),
    });
  }

  return (
    <>
      <button
        ref={buttonRef}
        className="session-row-main"
        onClick={onClick}
        onMouseEnter={showPreview}
        onMouseLeave={() => setPreviewPosition(null)}
        onFocus={showPreview}
        onBlur={() => setPreviewPosition(null)}
        aria-label={title}
      >
        {title}
      </button>
      {previewPosition &&
        createPortal(
          <div className="session-title-preview" role="tooltip" style={previewPosition}>
            <span className="session-title-preview-label">Chat title</span>
            {title}
          </div>,
          document.body,
        )}
    </>
  );
}

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

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("dba.theme");
    // Default to dark if no preference saved yet
    return saved ? saved === "dark" : true;
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("dba.theme", dark ? "dark" : "light");
  }, [dark]);
  return [dark, setDark];
}

export function App() {
  const [dark, setDark] = useDarkMode();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState("config");
  const [panelView, setPanelView] = useState("trace");
  const [traceSteps, setTraceSteps] = useState([]);
  const [evidenceCards, setEvidenceCards] = useState([]);
  const [usageInfo, setUsageInfo] = useState(null);
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
  const chatWindowRef = useRef(null);
  // Track whether the user has scrolled up so we don't hijack their position.
  const userScrolledUp = useRef(false);

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
    const win = chatWindowRef.current;
    if (!win) return;
    if (isRunning) {
      // During streaming: instant jump to bottom, no animation.
      // scrollIntoView stacks smooth-scroll animations (one per flush) and
      // that stacking is what reads as flicker. Direct scrollTop is instant
      // and idempotent — safe to call 16× per second.
      userScrolledUp.current = false;
      win.scrollTop = win.scrollHeight;
    } else if (!userScrolledUp.current) {
      // After streaming settles: smooth scroll only if the user hasn't
      // manually scrolled up to read earlier content.
      win.scrollTo({ top: win.scrollHeight, behavior: "smooth" });
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
    // A placeholder assistant message we grow as tokens stream in. Its created_at
    // is the stable key we use to patch the right bubble during the stream.
    const assistantCreatedAt = new Date(Date.now() + 1).toISOString();
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: "assistant", content: "", created_at: assistantCreatedAt, streaming: true }
    ]);
    setIsRunning(true);
    setError("");
    setRunProgress([]);
    // Reset the right-panel state for this turn; it persists after completion so
    // the last turn's trace + evidence stay visible until the next question.
    setTraceSteps([]);
    setEvidenceCards([]);
    setUsageInfo(null);

    function patchAssistant(patch) {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i -= 1) {
          if (next[i].role === "assistant" && next[i].created_at === assistantCreatedAt) {
            next[i] = { ...next[i], ...patch };
            break;
          }
        }
        return next;
      });
    }

    function pushProgress(message) {
      setRunProgress((prev) => [...prev, { timestamp: new Date().toISOString(), message }]);
    }

    let assistantContent = "";
    let finalSessionId = sessionId;
    let streamError = null;
    let succeeded = false;

    // Coalesce token writes. Patching React state on every token repaints the
    // whole bubble per character — that's the flicker. Buffer the deltas and
    // flush on a short timer so the text grows in smooth batches instead.
    let flushTimer = null;
    const flushTokens = () => {
      flushTimer = null;
      patchAssistant({ content: assistantContent });
    };
    const cancelFlush = () => {
      if (flushTimer !== null) {
        clearTimeout(flushTimer);
        flushTimer = null;
      }
    };

    // Track the current phase so the activity indicator stays meaningful through
    // mid-stream tool pauses (the "looks done, then resumes" gap is a tool run).
    let toolsInFlight = 0;
    let lastActivity = "";
    const setActivity = (message) => {
      if (message && message !== lastActivity) {
        lastActivity = message;
        pushProgress(message);
      }
    };

    try {
      await api.streamChat(
        {
          message: trimmed,
          max_turns: 30,
          session_id: sessionId,
          profile_id: profilesState.active_profile_id
        },
        (event, data) => {
          if (event === "token") {
            assistantContent += data.delta || "";
            if (toolsInFlight === 0) {
              setActivity("Composing the answer…");
            }
            if (flushTimer === null) {
              flushTimer = setTimeout(flushTokens, 60);
            }
          } else if (event === "tool_call") {
            toolsInFlight += 1;
            setActivity(`Calling ${data.label || data.tool}…`);
            const stepId = data.id || `step-${Date.now()}`;
            setTraceSteps((prev) => [
              ...prev,
              { id: stepId, label: data.label || data.tool, status: "running" }
            ]);
          } else if (event === "tool_result") {
            toolsInFlight = Math.max(0, toolsInFlight - 1);
            if (toolsInFlight === 0) {
              setActivity("Composing the answer…");
            }
            const nextStatus = data.status === "failed" ? "failed" : "done";
            setTraceSteps((prev) => {
              const byId = prev.some((step) => step.id === data.id);
              if (byId) {
                return prev.map((step) =>
                  step.id === data.id ? { ...step, status: nextStatus } : step
                );
              }
              // Fallback: settle the most recent still-running step.
              const idx = [...prev].reverse().findIndex((step) => step.status === "running");
              if (idx === -1) return prev;
              const realIdx = prev.length - 1 - idx;
              return prev.map((step, i) => (i === realIdx ? { ...step, status: nextStatus } : step));
            });
          } else if (event === "handoff") {
            setActivity(`Routing to ${data.to}…`);
            setTraceSteps((prev) => [
              ...prev,
              { id: `handoff-${prev.length}`, label: `Routing to ${data.to}`, status: "done" }
            ]);
          } else if (event === "evidence") {
            setEvidenceCards((prev) => [...prev, data]);
          } else if (event === "usage") {
            setUsageInfo(data);
          } else if (event === "done") {
            cancelFlush();
            assistantContent = data.final || assistantContent;
            finalSessionId = data.session_id || sessionId;
            patchAssistant({ content: assistantContent, streaming: false });
            setSessionId(finalSessionId);
            setLastResponseMetrics(data.metrics || null);
            const steps =
              data.next_steps && data.next_steps.length > 0
                ? data.next_steps
                : extractNextStepsFromText(assistantContent);
            setNextSteps(steps);
          } else if (event === "error") {
            streamError = data.message || "Stream failed.";
          }
        }
      );

      if (streamError) {
        throw new Error(streamError);
      }
      if (finalSessionId) {
        await refreshAll(finalSessionId);
      }
      succeeded = true;
    } catch (err) {
      cancelFlush();
      setError(err.message);
      // Roll back the optimistic turn. The composer keeps the rejected draft so
      // the user can edit and retry instead of losing their input.
      setMessages((prev) =>
        prev.filter(
          (item) =>
            item.created_at !== userMessage.created_at &&
            item.created_at !== assistantCreatedAt
        )
      );
    } finally {
      cancelFlush();
      setIsRunning(false);
      setRunProgress([]);
    }
    return succeeded;
  }

  async function handleSend(messageText) {
    return sendMessage(messageText);
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

  const activeProfile = profilesState.profiles.find(
    (item) => item.id === profilesState.active_profile_id
  );
  const requiredOk = configStatus?.required
    ? Object.values(configStatus.required).every(Boolean)
    : false;
  const connectionLabel = activeProfile
    ? activeProfile.name
    : envValues.DB_HOST || "Default (.env)";
  const connectionOk = apiConnected && requiredOk;

  return (
    <div className="app-root">
      <header className="top-bar">
        <div className="brand">
          <img src={mariadbLogo} alt="MariaDB" className="brand-logo" />
          <div className="brand-divider" aria-hidden="true" />
          <div className="brand-text">
            <span className="brand-name">{APP_NAME}</span>
            <span className="brand-tagline">{APP_TAGLINE}</span>
          </div>
        </div>
        <div className="top-bar-actions">
          <span
            className={connectionOk ? "conn-chip ok" : "conn-chip warn"}
            title={`Connection target: ${connectionLabel}`}
          >
            <span className="conn-dot" aria-hidden="true" />
            {connectionLabel}
          </span>
          <button className="ghost-button" onClick={startNewChat}>
            New chat
          </button>
          <a
            className="ghost-button"
            href={DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            title="Open documentation"
          >
            Docs
          </a>
          <a
            className="ghost-button github-star"
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            title="Star on GitHub"
          >
            <svg aria-hidden="true" height="14" viewBox="0 0 16 16" width="14" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            Star
          </a>
          <button
            className="ghost-button theme-toggle"
            onClick={() => setDark((d) => !d)}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? "☀" : "☾"}
          </button>
          <button className="ghost-button" onClick={() => setSettingsOpen(true)}>
            Settings
          </button>
        </div>
      </header>

      {!apiConnected && (
        <div className="banner warning">
          <span>
            Backend not connected. Start it with <code>./scripts/run_ui.sh</code>, then retry.
          </span>
          <button
            className="ghost-button"
            onClick={() =>
              refreshAll().catch((err) => {
                setApiConnected(false);
                setError(err.message);
                setIsLoadingBootstrap(false);
              })
            }
          >
            Retry
          </button>
        </div>
      )}
      {error && (
        <div className="banner error">
          <div>{error}</div>
          {errorHelp && <div className="error-help">{errorHelp}</div>}
        </div>
      )}

      <div className="workspace">
        {/* Left — Context: chats + quick prompts */}
        <aside className="context-col">
          <div className="context-section">
            <div className="context-head">Chats</div>
            <button
              className={!sessionId ? "session-row active" : "session-row"}
              onClick={startNewChat}
            >
              + New chat
            </button>
            {sessionsList
              .slice(-12)
              .reverse()
              .map((session) => (
                <div
                  key={session.id}
                  className={sessionId === session.id ? "session-row active" : "session-row"}
                >
                  <SessionTitleButton
                    title={session.title || "Chat"}
                    onClick={() => selectSession(session.id)}
                  />
                  <button
                    className="session-row-del"
                    onClick={() => deleteSessionById(session.id)}
                    aria-label={`Delete chat ${session.title || session.id}`}
                  >
                    ×
                  </button>
                </div>
              ))}
          </div>
          <div className="context-section">
            <div className="context-head">Quick prompts</div>
            <div className="starter-col">
              {STARTER_QUESTIONS.map((question) => (
                <button
                  key={question}
                  className="starter-row"
                  onClick={() => handleStarterQuestion(question)}
                  disabled={isRunning}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Center — Chat */}
        <main className="chat-col">
          {isLoadingBootstrap && messages.length === 0 && (
            <div className="info">Loading configuration and history…</div>
          )}
          <div
            className="chat-window"
            ref={chatWindowRef}
            onScroll={() => {
              const win = chatWindowRef.current;
              if (!win) return;
              const atBottom = win.scrollHeight - win.scrollTop - win.clientHeight < 80;
              userScrolledUp.current = !atBottom;
            }}
          >
            {messages.length === 0 && !isRunning && (
              <div className="empty-chat">
                <span className="empty-chat-mark" aria-hidden="true" />
                <h2>Ask DBA Pulse</h2>
                <p>{APP_BANNER_SUBLINE}</p>
                <div className="evidence-explainer">
                  <div className="evidence-explainer-item">
                    <span className="ee-icon">🔍</span>
                    <div>
                      <strong>Evidence-backed</strong>
                      <span>Every finding is grounded in real data — actual rows from <code>performance_schema</code>, slow query log entries, EXPLAIN plans. Open the Evidence tab to see exactly what the agent retrieved.</span>
                    </div>
                  </div>
                  <div className="evidence-explainer-item">
                    <span className="ee-icon">🔒</span>
                    <div>
                      <strong>Read-only</strong>
                      <span>The agent never writes to your database. All recommendations are suggestions — nothing is applied automatically.</span>
                    </div>
                  </div>
                  <div className="evidence-explainer-item">
                    <span className="ee-icon">🤖</span>
                    <div>
                      <strong>Multi-agent</strong>
                      <span>Specialist agents for slow queries, live queries, incident triage, replication, and ad-hoc SQL. The orchestrator routes and synthesises.</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {messages.map((message, idx) => {
              // The placeholder assistant bubble has no content until the first
              // token; the activity indicator stands in for it until then.
              if (message.role === "assistant" && message.streaming && !message.content) {
                return null;
              }
              return (
                <div className={`message ${message.role}`} key={`${message.created_at}-${idx}`}>
                  <div className="message-header">
                    <div className="message-role">{message.role}</div>
                    {message.role === "assistant" && !message.streaming && message.content && (
                      <CopyButton text={message.content} />
                    )}
                  </div>
                  <div className="markdown-body">
                    {message.streaming ? (
                      // Render raw text while streaming — re-parsing partial markdown
                      // every flush is what made it flicker. Markdown formatting is
                      // applied once the turn completes.
                      <div className="stream-text">
                        {message.content}
                        <span className="stream-cursor" aria-hidden="true" />
                      </div>
                    ) : (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                    )}
                  </div>
                </div>
              );
            })}
            {isRunning && (
              <div className="activity-indicator">
                <span className="activity-spinner" aria-hidden="true" />
                <span>{latestProgressMessage}</span>
              </div>
            )}
          </div>

          {nextSteps.length > 0 && (
            <div className="next-steps">
              <div>
                <h4>Next steps</h4>
                <ol>
                  {nextSteps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
            </div>
          )}

          <div className="composer">
            <ChatComposer onSend={handleSend} disabled={isRunning} />
          </div>
        </main>

        {/* Right — Evidence / Trace */}
        <EvidenceTracePanel
          view={panelView}
          setView={setPanelView}
          traceSteps={traceSteps}
          evidenceCards={evidenceCards}
          usage={usageInfo}
          isRunning={isRunning}
        />
      </div>

      {settingsOpen && (
        <div className="drawer-overlay" onClick={() => setSettingsOpen(false)}>
          <aside className="drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div className="drawer-tabs">
                {SETTINGS_TABS.map((tab) => (
                  <button
                    key={tab}
                    className={settingsTab === tab ? "drawer-tab active" : "drawer-tab"}
                    onClick={() => setSettingsTab(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>
              <button className="ghost-button" onClick={() => setSettingsOpen(false)}>
                Close
              </button>
            </div>
            <div className="drawer-body">
              {settingsTab === "config" && (
                <section>
                  <h3>Config</h3>
                  <p className="helper-text">
                    Loads from and saves to <code>mariadb_db_agents/.env</code>. Save creates a
                    backup at <code>.env.bak</code>.
                  </p>
                  <p className="helper-text">
                    Secret fields are masked. To change a secret, type a new value and save.
                  </p>
                  <p className="helper-text">
                    MariaDB Cloud API settings use the <code>MARIADB_CLOUD_*</code> prefix.
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
                          onChange={(e) =>
                            setEnvValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                          }
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
                          onChange={(e) =>
                            setEnvValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                          }
                        />
                      </label>
                    ))}
                  </div>
                  <button onClick={saveEnvValues}>Save .env values</button>
                </section>
              )}

              {settingsTab === "profiles" && (
                <section>
                  <h3>DB Profiles</h3>
                  <p className="helper-text">
                    Profiles are saved connection presets. Activate one to copy its DB values into{" "}
                    <code>.env</code> quickly.
                  </p>
                  <div className="profiles-list">
                    {profilesState.profiles.map((profile) => (
                      <div key={profile.id} className="profile-item">
                        <div>
                          <strong>{profile.name}</strong> - {profile.user}@{profile.host}:
                          {profile.port}/{profile.database}
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
                          onChange={(e) =>
                            setNewProfile((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                        />
                      </label>
                    ))}
                  </div>
                  <button onClick={createProfile}>Create profile</button>
                </section>
              )}

              {settingsTab === "agents" && (
                <section>
                  <h3>Agent Controls</h3>
                  <p className="helper-text">
                    Disable specialist tools you do not want Copilot to call.
                  </p>
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

              {settingsTab === "observability" && (
                <section>
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
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }
  return (
    <button className="copy-btn" onClick={copy} title="Copy response" aria-label="Copy response">
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

function ChatComposer({ onSend, disabled }) {
  const [draft, setDraft] = useState("");

  async function submit() {
    const message = draft.trim();
    if (!message || disabled) {
      return;
    }
    const sent = await onSend(message);
    if (sent) {
      setDraft("");
    }
  }

  return (
    <>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey || !e.shiftKey)) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask: Is my database healthy?"
        rows={4}
      />
      <div className="composer-actions">
        <span className="kbd-hint">⌘↵ or Enter to send · Shift+Enter for new line</span>
        <button onClick={submit} disabled={disabled}>
          {disabled ? "Analysing…" : "Send"}
        </button>
      </div>
    </>
  );
}

