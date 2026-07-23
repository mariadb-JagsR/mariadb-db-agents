const API_BASE = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options
    });
  } catch (error) {
    const message =
      `Cannot reach backend API at ${API_BASE}. ` +
      "Make sure the FastAPI server is running (use ./scripts/run_ui.sh) and try again.";
    throw new Error(message);
  }

  if (!response.ok) {
    let detail = "";
    try {
      const payload = await response.json();
      detail = payload.detail || payload.message || JSON.stringify(payload);
    } catch {
      detail = await response.text();
    }
    const message = detail
      ? `API ${response.status} (${path}): ${detail}`
      : `API ${response.status} (${path})`;
    throw new Error(message);
  }
  return response.json();
}

function parseSseFrame(frame) {
  let event = "message";
  const dataLines = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  const raw = dataLines.join("\n");
  let data = raw;
  try {
    data = JSON.parse(raw);
  } catch {
    /* keep the raw string if it isn't JSON */
  }
  return { event, data };
}

/**
 * Stream one orchestrator turn over SSE, invoking onEvent(event, data) per frame.
 * EventSource can't POST a body, so we read the fetch ReadableStream by hand and
 * split on the SSE frame delimiter (a blank line).
 */
async function streamChat(payload, onEvent, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE}/chat/orchestrator/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal
    });
  } catch (error) {
    throw new Error(
      `Cannot reach backend API at ${API_BASE}. ` +
        "Make sure the FastAPI server is running (use ./scripts/run_ui.sh) and try again."
    );
  }

  if (!response.ok || !response.body) {
    let detail = "";
    try {
      const payloadJson = await response.json();
      detail = payloadJson.detail || payloadJson.message || JSON.stringify(payloadJson);
    } catch {
      try {
        detail = await response.text();
      } catch {
        detail = "";
      }
    }
    throw new Error(
      detail
        ? `API ${response.status} (/chat/orchestrator/stream): ${detail}`
        : `API ${response.status} (/chat/orchestrator/stream)`
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let sepIndex;
    while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sepIndex);
      buffer = buffer.slice(sepIndex + 2);
      const parsed = parseSseFrame(frame);
      if (parsed) {
        onEvent(parsed.event, parsed.data);
      }
    }
  }
}

export const api = {
  health: () => request("/health"),
  chat: (payload) => request("/chat/orchestrator", { method: "POST", body: JSON.stringify(payload) }),
  streamChat,
  startChatRun: (payload) =>
    request("/chat/orchestrator/run", { method: "POST", body: JSON.stringify(payload) }),
  getChatRun: (runId) => request(`/chat/orchestrator/run/${runId}`),
  getConfigStatus: () => request("/config/status"),
  getEnvValues: () => request("/config/env-values"),
  updateEnv: (values) => request("/config/env", { method: "PUT", body: JSON.stringify({ values }) }),
  getProfiles: () => request("/profiles"),
  createProfile: (payload) => request("/profiles", { method: "POST", body: JSON.stringify(payload) }),
  updateProfile: (profileId, payload) =>
    request(`/profiles/${profileId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProfile: (profileId) => request(`/profiles/${profileId}`, { method: "DELETE" }),
  activateProfile: (profileId) => request(`/profiles/${profileId}/activate`, { method: "PUT" }),
  getToggles: () => request("/agents/toggles"),
  setToggles: (payload) => request("/agents/toggles", { method: "PUT", body: JSON.stringify(payload) }),
  setDefaultToggles: () => request("/agents/toggles/defaults", { method: "POST" }),
  getSessions: () => request("/sessions"),
  deleteSession: (sessionId) => request(`/sessions/${sessionId}`, { method: "DELETE" }),
  getObservability: () => request("/observability/summary")
};

