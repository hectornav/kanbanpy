import { useCallback, useEffect, useRef, useState } from "react";
import { api, connectLiveSync } from "./api.js";
import TaskModal from "./TaskModal.jsx";
import BoardSettingsModal from "./BoardSettingsModal.jsx";
import ActivityPanel from "./ActivityPanel.jsx";

const COLUMNS = [
  { key: "ToDo", label: "Por hacer", accent: "var(--todo)" },
  { key: "Doing", label: "En curso", accent: "var(--doing)" },
  { key: "Done", label: "Hecho", accent: "var(--done)" }
];

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
  const [boards, setBoards] = useState([]);
  const [activeId, setActiveId] = useState(() => Number(localStorage.getItem("kanban.board")) || null);
  const [board, setBoard] = useState({ ToDo: [], Doing: [], Done: [] });
  const [archived, setArchived] = useState([]);
  const [view, setView] = useState("board"); // board | archive
  const [users, setUsers] = useState([]);
  const [editing, setEditing] = useState(null);
  const [settingsFor, setSettingsFor] = useState(null); // board being created/edited
  const [showActivity, setShowActivity] = useState(false);
  const [dragId, setDragId] = useState(null);
  const [error, setError] = useState("");
  const [bg, setBg] = useState(readBg);
  const boardRef = useRef(board);
  boardRef.current = board;

  const active = boards.find((b) => b.id === activeId) || null;

  function changeBg(value) {
    setBg(value);
    localStorage.setItem("kanban.bg", JSON.stringify(value));
  }

  const loadBoards = useCallback(async () => {
    try {
      const list = await api.listBoards();
      setBoards(list);
      setActiveId((cur) => (list.some((b) => b.id === cur) ? cur : list[0]?.id ?? null));
    } catch (err) {
      setError(err.message);
      if (err.status === 401) onLogout();
    }
  }, [onLogout]);

  const loadTasks = useCallback(async () => {
    if (!activeId) return;
    try {
      if (view === "archive") setArchived((await api.boardTasks(activeId, true)).archived);
      else setBoard(await api.boardTasks(activeId, false));
    } catch (err) {
      setError(err.message);
    }
  }, [activeId, view]);

  useEffect(() => {
    loadBoards();
    api.users().then(setUsers).catch(() => {});
  }, [loadBoards]);

  useEffect(() => {
    loadTasks();
    const disconnect = connectLiveSync(() => {
      loadTasks();
      loadBoards();
    });
    return disconnect;
  }, [loadTasks, loadBoards]);

  useEffect(() => {
    if (activeId) localStorage.setItem("kanban.board", String(activeId));
  }, [activeId]);

  async function handleSave(data, id) {
    try {
      if (id) await api.updateTask(id, data);
      else await api.createTask(activeId, data);
      setEditing(null);
      await loadTasks();
    } catch (err) {
      setError(err.message);
    }
  }

  async function act(promise) {
    try {
      await promise;
      setEditing(null);
      await loadTasks();
    } catch (err) {
      setError(err.message);
    }
  }

  function onDrop(columnKey) {
    if (dragId == null) return;
    setDragId(null);
    const from = findColumn(boardRef.current, dragId);
    if (from === columnKey) return;
    api.moveTask(dragId, { column_name: columnKey }).then(loadTasks).catch((e) => setError(e.message));
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
          <button className="ghost" onClick={() => setShowActivity(true)} title="Actividad">🕘</button>
          <BackgroundPicker value={bg} onChange={changeBg} />
          <button className="ghost" onClick={onLogout}>Salir</button>
        </div>
      </header>

      <nav className="board-tabs">
        {boards.map((b) => (
          <button
            key={b.id}
            className={`tab${b.id === activeId ? " active" : ""}`}
            style={{ "--tab-c": b.color }}
            onClick={() => { setActiveId(b.id); setView("board"); }}
          >
            <span className="tab-dot" />
            {b.name}
            {b.is_shared ? " 🌐" : !b.is_owner ? " 🔗" : ""}
          </button>
        ))}
        <button className="tab add" onClick={() => setSettingsFor({ isNew: true })}>+ Tablero</button>
      </nav>

      {error && <div className="banner" onClick={() => setError("")}>{error} · toca para cerrar</div>}

      <div className="board-bar">
        <div className="seg">
          <button className={view === "board" ? "on" : ""} onClick={() => setView("board")}>Tablero</button>
          <button className={view === "archive" ? "on" : ""} onClick={() => setView("archive")}>Archivo</button>
        </div>
        <div className="board-bar-right">
          {view === "board" && (
            <button className="ghost" onClick={() => setEditing({ column_name: "ToDo" })}>+ Nueva tarea</button>
          )}
          {active?.is_owner && (
            <button className="ghost" onClick={() => setSettingsFor({ ...active })} title="Ajustes del tablero">⚙️</button>
          )}
        </div>
      </div>

      <div className="board-scroll" style={bgStyle(bg)}>
        {view === "board" ? (
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
                      onArchive={() => act(api.archiveTask(task.id))}
                    />
                  ))}
                  <button className="add-inline" onClick={() => setEditing({ column_name: col.key })}>
                    + Añadir
                  </button>
                </div>
              </section>
            ))}
          </div>
        ) : (
          <ArchiveList
            items={archived}
            onRestore={(id) => act(api.restoreTask(id))}
            onDelete={(id) => act(api.deleteTask(id))}
          />
        )}
      </div>

      {editing && (
        <TaskModal
          task={editing}
          canDelete={editing.id != null && (editing.owner_id === user.id || active?.is_owner)}
          canArchive={editing.id != null}
          onClose={() => setEditing(null)}
          onSave={handleSave}
          onDelete={(id) => act(api.deleteTask(id))}
          onArchive={(id) => act(api.archiveTask(id))}
        />
      )}

      {settingsFor && (
        <BoardSettingsModal
          board={settingsFor}
          users={users}
          onClose={() => setSettingsFor(null)}
          onSaved={async (newId) => {
            setSettingsFor(null);
            await loadBoards();
            if (newId) { setActiveId(newId); setView("board"); }
          }}
          onDeleted={async () => { setSettingsFor(null); await loadBoards(); }}
          onError={setError}
        />
      )}

      {showActivity && active && (
        <ActivityPanel boardId={active.id} boardName={active.name} onClose={() => setShowActivity(false)} />
      )}
    </div>
  );
}

function TaskCard({ task, isOwner, onDragStart, onClick, onArchive }) {
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
      <button
        className="card-archive"
        title="Archivar"
        onClick={(e) => { e.stopPropagation(); onArchive(); }}
      >
        ✓
      </button>
      <p className="card-text">{task.text}</p>
      <div className="card-meta">
        {task.priority && <span className={`prio prio-${prio}`}>{prioLabel(task.priority)}</span>}
        {task.tags?.map((t) => (
          <span className="chip" key={t}>{t}</span>
        ))}
        {task.due_date && <span className="due">📅 {task.due_date}</span>}
        {!isOwner && <span className="shared" title="De otro usuario">👤</span>}
      </div>
    </article>
  );
}

function ArchiveList({ items, onRestore, onDelete }) {
  if (!items.length) {
    return <div className="empty">Aún no hay tareas archivadas. Marca una tarea como ✓ para archivarla.</div>;
  }
  return (
    <div className="archive-list">
      {items.map((t) => (
        <div className="archive-row" key={t.id}>
          <div className="archive-main">
            <span className={`dot dot-${t.column_name}`} />
            <span className="archive-text">{t.text}</span>
            {t.archived_at && <span className="archive-date">archivada {t.archived_at.slice(0, 10)}</span>}
          </div>
          <div className="archive-actions">
            <button className="ghost" onClick={() => onRestore(t.id)}>Restaurar</button>
            <button className="danger" onClick={() => onDelete(t.id)}>Eliminar</button>
          </div>
        </div>
      ))}
    </div>
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
              const activeSel =
                (b.id === "graphite" && value.type === "default") ||
                (value.type === "preset" && value.value === b.id);
              return (
                <button
                  key={b.id}
                  className={`bg-swatch${activeSel ? " active" : ""}`}
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
