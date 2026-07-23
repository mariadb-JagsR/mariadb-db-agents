import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const KIND_BADGE = {
  slow_log: "Slow log",
  processlist: "Processlist",
  triage: "Triage",
  replication: "Replication",
  sql: "SQL",
  observability: "Observability",
  evidence: "Evidence"
};

function StatusDot({ status }) {
  if (status === "running") {
    return <span className="trace-dot running" aria-label="running" />;
  }
  if (status === "failed") {
    return (
      <span className="trace-dot failed" aria-label="failed">
        ×
      </span>
    );
  }
  return (
    <span className="trace-dot done" aria-label="done">
      ✓
    </span>
  );
}

/**
 * The right-hand workspace panel. Two views over the current turn:
 *  - Trace: the agent's tool calls + routing, live, with token usage.
 *  - Evidence: the reports/metrics each specialist tool produced, as cards.
 * Both are fed by the SSE stream (tool_call/tool_result/handoff/evidence/usage)
 * and reset per turn in App.sendMessage.
 */
export function EvidenceTracePanel({ view, setView, traceSteps, evidenceCards, usage, isRunning }) {
  return (
    <aside className="evidence-col">
      <div className="evidence-tabs" role="tablist">
        <button
          role="tab"
          className={view === "evidence" ? "evidence-tab active" : "evidence-tab"}
          onClick={() => setView("evidence")}
        >
          Evidence{evidenceCards.length > 0 ? ` · ${evidenceCards.length}` : ""}
        </button>
        <button
          role="tab"
          className={view === "trace" ? "evidence-tab active" : "evidence-tab"}
          onClick={() => setView("trace")}
        >
          Trace{traceSteps.length > 0 ? ` · ${traceSteps.length}` : ""}
        </button>
      </div>
      <div className="evidence-body">
        {view === "trace" ? (
          <TraceView steps={traceSteps} usage={usage} isRunning={isRunning} />
        ) : (
          <EvidenceView cards={evidenceCards} isRunning={isRunning} />
        )}
      </div>
    </aside>
  );
}

function TraceView({ steps, usage, isRunning }) {
  if (steps.length === 0) {
    return (
      <div className="panel-empty">
        {isRunning
          ? "Tracing the agent's steps…"
          : "Tool calls and agent routing appear here as the Copilot works through your question."}
      </div>
    );
  }
  return (
    <div className="trace-list">
      {steps.map((step) => (
        <div className={`trace-step ${step.status}`} key={step.id}>
          <StatusDot status={step.status} />
          <span className="trace-step-label">{step.label}</span>
        </div>
      ))}
      {usage && (
        <div className="trace-usage">
          <div className="trace-usage-row">
            <span>Round trips</span>
            <strong>{usage.round_trips ?? "—"}</strong>
          </div>
          <div className="trace-usage-row">
            <span>Total tokens</span>
            <strong>{(usage.tokens ?? 0).toLocaleString()}</strong>
          </div>
          {(usage.by_agent || []).map((agent) => (
            <div className="trace-usage-row sub" key={agent.agent}>
              <span>{agent.agent}</span>
              <span>{(agent.tokens || 0).toLocaleString()} tok</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EvidenceView({ cards, isRunning }) {
  if (cards.length === 0) {
    return (
      <div className="panel-empty">
        {isRunning
          ? "Gathering evidence…"
          : "Evidence the Copilot gathered — query results, health reports, metrics — appears here, each tied to the specialist tool that produced it."}
      </div>
    );
  }
  return (
    <div className="evidence-list">
      {cards.map((card, idx) => (
        <details className="evidence-card" key={card.id || idx} open={idx === cards.length - 1}>
          <summary className="evidence-card-head">
            <span className="kind-badge">{KIND_BADGE[card.kind] || card.kind || "Evidence"}</span>
            <span className="evidence-card-title">{card.title}</span>
          </summary>
          <div className="evidence-card-body markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {typeof card.payload === "string"
                ? card.payload
                : "```json\n" + JSON.stringify(card.payload, null, 2) + "\n```"}
            </ReactMarkdown>
          </div>
        </details>
      ))}
    </div>
  );
}
