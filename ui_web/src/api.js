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

export const api = {
  health: () => request("/health"),
  chat: (payload) => request("/chat/orchestrator", { method: "POST", body: JSON.stringify(payload) }),
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

