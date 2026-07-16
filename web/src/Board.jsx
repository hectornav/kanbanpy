import { useCallback, useEffect, useRef, useState } from "react";
import { api, auth, connectLiveSync } from "./api.js";
import TaskModal from "./TaskModal.jsx";

const COLUMNS = [
  { key: "ToDo", label: "Por hacer", accent: "var(--todo)" },
  { key: "Doing", label: "En curso", accent: "var(--doing)" },
  { key: "Done", label: "Hecho", accent: "var(--done)" }
];

// Selectable board backgrounds (persisted in localStorage).
const BACKGROUNDS = [
  { id: "graphite", css: "", preview: "#0b0c10" },
  { id: "aurora",
    css: "radial-gradient(900px 520px at 12% -10%, rgba(62,207,142,0.20), transparent), radial-gradient(820px 520px at 100% 0%, rgba(91,140,255,0.22), transparent)",
    preview: "linear-gradient(135deg,#3ecf8e,#5b8cff)" },
  { id: "sunset",
    css: "linear-gradient(165deg, rgba(240,164,58,0.24), rgba(229,72,77,0.16) 55%, transparent 88%)",
    preview: "linear-gradient(135deg,#f0a43a,#e5484d)" },
  { id: "ocean",
    css: "linear-gradient(165deg, rgba(65,102,230,0.26), rgba(62,207,142,0.14))",
    preview: "linear-gradient(135deg,#4166e6,#3ecf8e)" },
  { id: "violet",
    css: "radial-gradient(820px 520px at 30% -6%, rgba(139,92,246,0.28), transparent), radial-gradient(720px 520px at 100% 10%, rgba(91,140,255,0.18), transparent)",
    preview: "linear-gradient(135deg,#8b5cf6,#5b8cff)" }
];

function readBg() {
  try {
    return JSON.parse(localStorage.getItem("kanban.bg")) || { type: "default" };
  } catch {
    return { type: "default" };
  }
}

function bgStyle(value) {
  if (value.type === "color") return { backgroundColor: value.value, backgroundImage: "none" };
  if (value.type === "preset") {
    const b = BACKGROUNDS.find((x) => x.id === value.value);
    if (b?.css) return { backgroundColor: "var(--ground)", backgroundImage: b.css };
  }
  return undefined;
}

export default function Board({ user, onLogout }) {
  const [board, setBoard] = useState({ ToDo: [], Doing: [], Done: [] });
  const [users, setUsers] = useState([]);
  const [editing, setEditing] = useState(null); // task object or {column} for new
  const [dragId, setDragId] = useState(null);
  const [error, setError] = useState("");
  const [bg, setBg] = useState(readBg);

  function changeBg(value) {
    setBg(value);
    localStorage.setItem("kanban.bg", JSON.stringify(value));
  }
  const boardRef = useRef(board);
  boardRef.current = board;

  const load = useCallback(async () => {
    try {
      setBoard(await api.board());
    } catch (err) {
      setError(err.message);
      if (err.status === 401) onLogout();
    }
  }, [onLogout]);

  useEffect(() => {
    load();
    api.users().then(setUsers).catch(() => {});
    const disconnect = connectLiveSync(() => load());
    return disconnect;
  }, [load]);

  async function handleSave(data, id) {
    try {
      if (id) await api.updateTask(id, data);
      else await api.createTask(data);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    try {
      await api.deleteTask(id);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  // ── Drag & drop between columns ──
  function onDrop(columnKey) {
    if (dragId == null) return;
    setDragId(null);
    // Optimistic move, then persist.
    const from = findColumn(boardRef.current, dragId);
    if (from === columnKey) return;
    api.moveTask(dragId, { column_name: columnKey }).then(load).catch((e) => setError(e.message));
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mini">
          <span className="logo-mark sm">📋</span>
          <strong>Kanbanpy Pro</strong>
        </div>
        <div className="topbar-right">
          <span className="who">@{user.username}</span>
          <BackgroundPicker value={bg} onChange={changeBg} />
          <button className="ghost" onClick={() => setEditing({ column_name: "ToDo" })}>+ Nueva tarea</button>
          <button className="ghost" onClick={onLogout}>Salir</button>
        </div>
      </header>

      {error && <div className="banner" onClick={() => setError("")}>{error} · toca para cerrar</div>}

      <div className="board-scroll" style={bgStyle(bg)}>
        <div className="board-grid">
          {COLUMNS.map((col) => (
            <section
              key={col.key}
              className="board-col"
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(col.key)}
            >
              <div className="col-head" style={{ "--accent": col.accent }}>
                <span className="col-title">{col.label}</span>
                <span className="col-count">{board[col.key]?.length || 0}</span>
              </div>
              <div className="col-body">
                {(board[col.key] || []).map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    isOwner={task.owner_id === user.id}
                    onDragStart={() => setDragId(task.id)}
                    onClick={() => setEditing(task)}
                  />
                ))}
                <button className="add-inline" onClick={() => setEditing({ column_name: col.key })}>
                  + Añadir
                </button>
              </div>
            </section>
          ))}
        </div>
      </div>

      {editing && (
        <TaskModal
          task={editing}
          users={users}
          canDelete={editing.id != null && editing.owner_id === user.id}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}

function TaskCard({ task, isOwner, onDragStart, onClick }) {
  const prio = (task.priority || "").toLowerCase();
  return (
    <article
      className={`card card-${task.column_name}`}
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <p className="card-text">{task.text}</p>
      <div className="card-meta">
        {task.priority && <span className={`prio prio-${prio}`}>{prioLabel(task.priority)}</span>}
        {task.tags?.map((t) => (
          <span className="chip" key={t}>{t}</span>
        ))}
        {task.due_date && <span className="due">📅 {task.due_date}</span>}
        {task.is_shared && <span className="shared" title="Compartida">👥</span>}
        {!isOwner && <span className="shared" title="Compartida contigo">🔗</span>}
      </div>
    </article>
  );
}

function BackgroundPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-picker">
      <button className="ghost" onClick={() => setOpen((o) => !o)} title="Fondo del tablero" aria-label="Fondo">🎨</button>
      {open && (
        <div className="bg-panel" onMouseLeave={() => setOpen(false)}>
          <p className="lbl">Fondo del tablero</p>
          <div className="bg-swatches">
            {BACKGROUNDS.map((b) => {
              const active =
                (b.id === "graphite" && value.type === "default") ||
                (value.type === "preset" && value.value === b.id);
              return (
                <button
                  key={b.id}
                  className={`bg-swatch${active ? " active" : ""}`}
                  style={{ background: b.preview }}
                  title={b.id}
                  aria-label={b.id}
                  onClick={() => onChange(b.id === "graphite" ? { type: "default" } : { type: "preset", value: b.id })}
                />
              );
            })}
          </div>
          <label className="bg-custom">
            <span>Color personalizado</span>
            <input
              type="color"
              value={value.type === "color" ? value.value : "#0b0c10"}
              onChange={(e) => onChange({ type: "color", value: e.target.value })}
            />
          </label>
        </div>
      )}
    </div>
  );
}

function prioLabel(p) {
  return { High: "Alta", Medium: "Media", Low: "Baja" }[p] || p;
}

function findColumn(board, id) {
  for (const key of Object.keys(board)) {
    if (board[key].some((t) => t.id === id)) return key;
  }
  return null;
}
