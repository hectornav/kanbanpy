// api.js - thin fetch wrapper around the Kanbanpy Pro REST API + live-sync socket.

const TOKEN_KEY = "kanban.token";

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(v) {
    if (v) localStorage.setItem(TOKEN_KEY, v);
    else localStorage.removeItem(TOKEN_KEY);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  }
};

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (res.status === 401) {
    auth.clear();
    throw new ApiError("Session expired. Please sign in again.", 401);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    throw new ApiError(data?.detail || "Something went wrong.", res.status);
  }
  return data;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const api = {
  register: (payload) => request("/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload }),
  me: () => request("/auth/me"),
  securityQuestion: (username) =>
    request(`/auth/security-question?username=${encodeURIComponent(username)}`),
  resetPassword: (payload) => request("/auth/reset-password", { method: "POST", body: payload }),

  board: () => request("/board"),
  users: () => request("/users"),
  createTask: (task) => request("/tasks", { method: "POST", body: task }),
  updateTask: (id, task) => request(`/tasks/${id}`, { method: "PUT", body: task }),
  moveTask: (id, payload) => request(`/tasks/${id}/move`, { method: "POST", body: payload }),
  reorder: (payload) => request("/columns/reorder", { method: "POST", body: payload }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
  taskShares: (id) => request(`/tasks/${id}/shares`)
};

// Live sync: reconnecting WebSocket that calls onChange when the board mutates.
export function connectLiveSync(onChange) {
  let socket = null;
  let closed = false;
  let retry = 1000;

  function open() {
    if (closed || !auth.token) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${proto}://${location.host}/ws?token=${auth.token}`);
    socket.onopen = () => {
      retry = 1000;
    };
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "board:changed") onChange(msg);
      } catch {
        /* ignore */
      }
    };
    socket.onclose = () => {
      if (closed) return;
      setTimeout(open, retry);
      retry = Math.min(retry * 2, 15000);
    };
  }
  open();

  return () => {
    closed = true;
    socket?.close();
  };
}
