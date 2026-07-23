# UI/UX Redesign Plan — Evolving the Operations Copilot toward LogGoblin's UX

**Goal:** Borrow the interaction patterns that make the LogGoblin support tool feel
better — real token streaming, a persistent 3-panel layout, evidence cards with
inline citations, a tool-call trace timeline, source chips, and a polished brand
design system — and apply them to **our existing** `ui_web` + `ui_api`, rather
than rebuilding from scratch.

This plan is grounded in the current code, not a greenfield assumption.

---

## 1. What we already have (and should keep)

**Frontend — `ui_web/` (Vite + React, single [App.jsx](../ui_web/src/App.jsx), ~713 lines):**
- Tab nav: chat · config · profiles · agents · observability
- Chat: markdown messages, composer (Enter-to-send), session pills, starter
  questions, "Next Steps" text-extraction, optional Insights side panel
- **Features LogGoblin lacks and we must not lose:** `.env` Config editor, DB
  connection **Profiles**, per-agent **toggles**, session history.

**Backend — `ui_api/` (FastAPI):**
- [orchestrator_service.py](../ui_api/orchestrator_service.py): runs the orchestrator
  via `Runner.run`, tracks `InteractionMetrics` (incl. sub-agent breakdown).
- Run model is **fire-and-poll**: `start_orchestrator_chat_run` spawns a task;
  the UI polls `get_orchestrator_chat_run` every 600ms ([App.jsx:211](../ui_web/src/App.jsx)).
- [progress.py](../ui_api/progress.py): a `ContextVar` `publish_progress(message)`
  callback appends string events to the run — a primitive trace.

## 2. The gap vs. LogGoblin (what to borrow, ranked by impact)

| # | Borrow | Current state here | Why it matters |
|---|---|---|---|
| 1 | **Token streaming** | Polls every 600ms; answer appears all at once | The single biggest "feels better" difference. Visceral. |
| 2 | **3-panel layout** (Context · Chat · Evidence/Trace) | Full-screen tabs | Evidence + chat visible together; no context-switching |
| 3 | **Evidence cards + inline `[n]` markers** | "Next Steps" text-scrape only | Every recommendation links to the live query/metric that backs it — the DBA trust mechanic |
| 4 | **Trace timeline** | "Live Progress" string messages | We already collect tool calls + `sub_agent_metrics`; render them as a real timeline with status + token badges |
| 5 | **Per-turn source chips** | none | Show which sources informed each answer (perf_schema, slow_log, MariaDB Cloud observability) |
| 6 | **shadcn/Tailwind + MariaDB brand tokens** | 812 lines hand-rolled CSS | The polished look the user flagged. oklch teal palette + accent rule |

**Reframe for #3:** LogGoblin's citations are RAG retrievals from a corpus. We
have no corpus, so **"evidence" = the live tool output the orchestrator gathered**
(each specialist's result, EXPLAIN plans, processlist rows, perf_schema digests,
MariaDB Cloud snapshots). For a DBA this is *more* convincing than text citations.

## 3. The pivotal backend change: `Runner.run` → `Runner.run_streamed` + SSE

Replace the poll loop with a Server-Sent-Events stream. The SDK's
`Runner.run_streamed(...).stream_events()` already emits exactly what the new UI
panels need — richer than the manual `publish_progress` strings:

| SDK stream event | SSE event | UI consumer |
|---|---|---|
| raw `response.output_text.delta` | `token {delta}` | chat text streams live |
| run-item `tool_called` | `tool_call {id,tool,args}` | Trace node start |
| run-item `tool_output` | `tool_result {id,status,summary}` + `evidence {id,kind,title,payload}` | Trace node done + Evidence card |
| agent handoff / `agent_updated` | `handoff {to}` | Trace routing edge |
| end of run → `InteractionMetrics` | `usage {round_trips,tokens,by_agent}` | usage badges |
| final | `done {final}` | end of turn |

Add a new endpoint (e.g. `POST /chat/orchestrator/stream`, `text/event-stream`)
alongside the existing run endpoints, so the poll path keeps working during the
transition. The session-append + run-history + next-steps logic in
`_run_orchestrator_chat_internal` is reused; only the `Runner.run` call and the
response shape change. Frontend consumes it with `fetch` + a `ReadableStream`
reader (EventSource can't POST a body).

## 4. The open decision (settle before building the frontend)

**Path A — Evolve `ui_web` in place (recommended).** Keep Vite + React; refactor
`App.jsx` into the 3-panel shell; add SSE streaming, Evidence + Trace panels;
restyle with Tailwind + brand tokens. Config/profiles/agents move into the left
Context panel or a settings drawer. *Pros:* reuses the working FastAPI backend and
the config/profiles/sessions/toggles features; lower risk. *Cons:* manual port of
LogGoblin's React components (different build than its Next.js).

**Path B — Rebuild as Next.js + shadcn mirroring LogGoblin.** *Pros:* maximum
component reuse from LogGoblin; cleanest design-system adoption. *Cons:* discards a
working SPA and re-implements config/profiles/sessions; larger effort.

## 5. Suggested build order (Path A)

1. **SSE streaming endpoint** in `ui_api` over `Runner.run_streamed` — emit
   `token` + `done` first. Verify with `curl -N`. (De-risks everything; biggest
   felt improvement.)
2. **Frontend streaming** — switch the chat send path from poll to SSE reader;
   tokens render live. Keep the current layout for this step.
3. **3-panel shell** — refactor `App.jsx`; Context (left) / Chat (center) /
   Evidence·Trace (right). Fold config/profiles/agents into Context or a drawer.
4. **Trace panel** — emit `tool_call`/`handoff`/`usage`; render the timeline
   (data already exists in `sub_agent_metrics`).
5. **Evidence panel** — emit `evidence` cards from tool outputs; wire inline `[n]`.
6. **Source chips** + **restyle** with Tailwind + MariaDB oklch tokens.

Each step is independently demoable; nothing requires a big-bang switch.

## Status (updated as we build)

- ✅ **Step 1** — SSE endpoint (`POST /chat/orchestrator/stream`) over `Runner.run_streamed`.
- ✅ **Step 2** — frontend consumes the stream; text grows live (buffered flush, plain-text-while-streaming to kill flicker, persistent activity indicator).
- ✅ **Step 3** — persistent 3-panel workspace (Context · Chat · Evidence/Trace); settings (config/profiles/agents/observability) moved to a slide-over drawer; connection chip + empty state.
- ✅ **Trace + Evidence panels** — fed live by `tool_call`/`tool_result`/`handoff`/`evidence`/`usage`.
- ⏭️ **Next** — richer per-probe evidence cards (EXPLAIN/processlist/perf_schema rows from specialist tools), inline `[n]` citation markers, per-turn source chips, and a final design pass (Tailwind/brand tokens optional).

## 6. Notes
- Single-operator local tool (current assumption); no auth work planned.
- Connection target stays driven by `.env` / Profiles as today.
- Future: the Evidence panel is designed to also host RAG/precedent cards if we
  later integrate a knowledge corpus (see the LogGoblin complementarity analysis).
