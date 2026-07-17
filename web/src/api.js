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

  // Boards
  listBoards: () => request("/boards"),
  createBoard: (payload) => request("/boards", { method: "POST", body: payload }),
  updateBoard: (id, payload) => request(`/boards/${id}`, { method: "PUT", body: payload }),
  deleteBoard: (id) => request(`/boards/${id}`, { method: "DELETE" }),
  boardMembers: (id) => request(`/boards/${id}/members`),
  boardActivity: (id) => request(`/boards/${id}/activity`),

  // Tasks
  users: () => request("/users"),
  boardTasks: (boardId, archived = false) =>
    request(`/boards/${boardId}/tasks${archived ? "?archived=true" : ""}`),
  createTask: (boardId, task) => request(`/boards/${boardId}/tasks`, { method: "POST", body: task }),
  updateTask: (id, task) => request(`/tasks/${id}`, { method: "PUT", body: task }),
  moveTask: (id, payload) => request(`/tasks/${id}/move`, { method: "POST", body: payload }),
  reorder: (payload) => request("/columns/reorder", { method: "POST", body: payload }),
  archiveTask: (id) => request(`/tasks/${id}/archive`, { method: "POST" }),
  restoreTask: (id) => request(`/tasks/${id}/restore`, { method: "POST" }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),

  // Task detail
  taskDetail: (id) => request(`/tasks/${id}`),
  addSubtask: (id, text) => request(`/tasks/${id}/subtasks`, { method: "POST", body: { text } }),
  updateSubtask: (sid, payload) => request(`/subtasks/${sid}`, { method: "PUT", body: payload }),
  deleteSubtask: (sid) => request(`/subtasks/${sid}`, { method: "DELETE" }),
  addComment: (id, body) => request(`/tasks/${id}/comments`, { method: "POST", body: { body } }),
  deleteComment: (cid) => request(`/comments/${cid}`, { method: "DELETE" }),

  // AI planner
  aiStatus: () => request("/ai/status"),
  aiPlan: (boardId, idea) => request(`/boards/${boardId}/ai-plan`, { method: "POST", body: { idea } }),

  // Push notifications
  pushPublicKey: () => request("/push/public-key"),
  pushSubscribe: (subscription) => request("/push/subscribe", { method: "POST", body: subscription }),
  pushUnsubscribe: (endpoint) => request("/push/unsubscribe", { method: "POST", body: { endpoint } })
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
