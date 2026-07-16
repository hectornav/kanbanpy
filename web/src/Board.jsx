import { useCallback, useEffect, useState } from "react";
import {
  DndContext, PointerSensor, TouchSensor, useSensor, useSensors, closestCorners, useDroppable
} from "@dnd-kit/core";
import {
  SortableContext, useSortable, arrayMove, verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, connectLiveSync } from "./api.js";
import { enablePush, disablePush, isPushEnabled, pushSupported } from "./push.js";
import TaskModal from "./TaskModal.jsx";
import BoardSettingsModal from "./BoardSettingsModal.jsx";
import ActivityPanel from "./ActivityPanel.jsx";

const COLUMNS = [
  { key: "ToDo", label: "Por hacer", accent: "var(--todo)" },
  { key: "Doing", label: "En curso", accent: "var(--doing)" },
  { key: "Done", label: "Hecho", accent: "var(--done)" }
];
const COLUMN_KEYS = COLUMNS.map((c) => c.key);

const THEMES = [
  { id: "nocturne", name: "Nocturne", sub: "Pizarra fría", chips: ["#0d1017", "#6d8bff", "#37d69f"] },
  { id: "frost", name: "Frost", sub: "Claro y nítido", chips: ["#eef1f6", "#2f5fe0", "#0a9d5f"] },
  { id: "meridian", name: "Meridian", sub: "Grafito cálido", chips: ["#131110", "#ff8a5c", "#4fd6b0"] }
];

const BACKGROUNDS = [
  { id: "default", css: "", preview: "var(--ground)" },
  { id: "aurora",
    css: "radial-gradient(900px 520px at 12% -10%, rgba(62,207,142,0.16), transparent), radial-gradient(820px 520px at 100% 0%, rgba(91,140,255,0.18), transparent)",
    preview: "linear-gradient(135deg,#3ecf8e,#5b8cff)" },
  { id: "ocean",
    css: "linear-gradient(165deg, rgba(65,102,230,0.20), rgba(62,207,142,0.10))",
    preview: "linear-gradient(135deg,#4166e6,#3ecf8e)" },
  { id: "violet",
    css: "radial-gradient(820px 520px at 30% -6%, rgba(139,92,246,0.22), transparent)",
    preview: "linear-gradient(135deg,#8b5cf6,#5b8cff)" }
];

function readBg() {
  try { return JSON.parse(localStorage.getItem("kanban.bg")) || { type: "default" }; }
  catch { return { type: "default" }; }
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
  const [view, setView] = useState("board");
  const [users, setUsers] = useState([]);
  const [editing, setEditing] = useState(null);
  const [settingsFor, setSettingsFor] = useState(null);
  const [showActivity, setShowActivity] = useState(false);
  const [error, setError] = useState("");
  const [bg, setBg] = useState(readBg);

  const active = boards.find((b) => b.id === activeId) || null;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 180, tolerance: 8 } })
  );

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
    const disconnect = connectLiveSync(() => { loadTasks(); loadBoards(); });
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
    } catch (err) { setError(err.message); }
  }

  async function act(promise) {
    try { await promise; setEditing(null); await loadTasks(); }
    catch (err) { setError(err.message); }
  }

  // ── Drag & drop (touch-friendly, with within-column reordering) ──
  const findContainer = (id) => (COLUMN_KEYS.includes(id) ? id : COLUMN_KEYS.find((k) => board[k].some((t) => t.id === id)));

  function onDragOver({ active: a, over }) {
    if (!over) return;
    const from = findContainer(a.id);
    const to = findContainer(over.id);
    if (!from || !to || from === to) return;
    setBoard((prev) => {
      const item = prev[from].find((t) => t.id === a.id);
      if (!item) return prev;
      const overIdx = prev[to].findIndex((t) => t.id === over.id);
      const insertAt = overIdx >= 0 ? overIdx : prev[to].length;
      return {
        ...prev,
        [from]: prev[from].filter((t) => t.id !== a.id),
        [to]: [...prev[to].slice(0, insertAt), item, ...prev[to].slice(insertAt)]
      };
    });
  }

  function onDragEnd({ active: a, over }) {
    if (!over) return;
    const to = findContainer(over.id);
    if (!to) return;
    setBoard((prev) => {
      const items = prev[to];
      const oldIdx = items.findIndex((t) => t.id === a.id);
      const overIdx = items.findIndex((t) => t.id === over.id);
      const next = oldIdx !== -1 && overIdx !== -1 && oldIdx !== overIdx
        ? { ...prev, [to]: arrayMove(items, oldIdx, overIdx) }
        : prev;
      persistOrder(next);
      return next;
    });
  }

  function persistOrder(next) {
    Promise.all(
      COLUMN_KEYS.map((col) =>
        api.reorder({ board_id: activeId, column_name: col, ordered_ids: next[col].map((t) => t.id) })
      )
    ).catch((e) => { setError(e.message); loadTasks(); });
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
          <PushToggle onError={setError} />
          <button className="ghost" onClick={() => setShowActivity(true)} title="Actividad">🕘</button>
          <ThemePicker />
          <BackgroundPicker value={bg} onChange={changeBg} />
          <button className="ghost" onClick={onLogout}>Salir</button>
        </div>
      </header>

      <nav className="board-tabs">
        {boards.map((b) => (
          <button key={b.id} className={`tab${b.id === activeId ? " active" : ""}`} style={{ "--tab-c": b.color }}
            onClick={() => { setActiveId(b.id); setView("board"); }}>
            <span className="tab-dot" />
            {b.name}{b.is_shared ? " 🌐" : !b.is_owner ? " 🔗" : ""}
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
          {view === "board" && <button className="ghost" onClick={() => setEditing({ column_name: "ToDo" })}>+ Nueva tarea</button>}
          {active?.is_owner && <button className="ghost" onClick={() => setSettingsFor({ ...active })} title="Ajustes del tablero">⚙️</button>}
        </div>
      </div>

      <div className="board-scroll" style={bgStyle(bg)}>
        {view === "board" ? (
          <DndContext sensors={sensors} collisionDetection={closestCorners} onDragOver={onDragOver} onDragEnd={onDragEnd}>
            <div className="board-grid">
              {COLUMNS.map((col) => (
                <Column key={col.key} col={col} tasks={board[col.key] || []}
                  currentUserId={user.id}
                  onAdd={() => setEditing({ column_name: col.key })}
                  onOpen={setEditing}
                  onArchive={(id) => act(api.archiveTask(id))} />
              ))}
            </div>
          </DndContext>
        ) : (
          <ArchiveList items={archived} onRestore={(id) => act(api.restoreTask(id))} onDelete={(id) => act(api.deleteTask(id))} />
        )}
      </div>

      {editing && (
        <TaskModal task={editing}
          canDelete={editing.id != null && (editing.owner_id === user.id || active?.is_owner)}
          canArchive={editing.id != null}
          onClose={() => setEditing(null)} onSave={handleSave}
          onDelete={(id) => act(api.deleteTask(id))} onArchive={(id) => act(api.archiveTask(id))} />
      )}
      {settingsFor && (
        <BoardSettingsModal board={settingsFor} users={users}
          onClose={() => setSettingsFor(null)}
          onSaved={async (newId) => { setSettingsFor(null); await loadBoards(); if (newId) { setActiveId(newId); setView("board"); } }}
          onDeleted={async () => { setSettingsFor(null); await loadBoards(); }}
          onError={setError} />
      )}
      {showActivity && active && (
        <ActivityPanel boardId={active.id} boardName={active.name} onClose={() => setShowActivity(false)} />
      )}
    </div>
  );
}

function Column({ col, tasks, currentUserId, onAdd, onOpen, onArchive }) {
  const { setNodeRef, isOver } = useDroppable({ id: col.key });
  return (
    <section className="board-col">
      <div className="col-head" style={{ "--accent": col.accent }}>
        <span className="col-title">{col.label}</span>
        <span className="col-count">{tasks.length}</span>
      </div>
      <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className={`col-body${isOver ? " drop-over" : ""}`}>
          {tasks.map((task) => (
            <SortableCard key={task.id} task={task} isOwner={task.owner_id === currentUserId}
              onClick={() => onOpen(task)} onArchive={() => onArchive(task.id)} />
          ))}
          <button className="add-inline" onClick={onAdd}>+ Añadir</button>
        </div>
      </SortableContext>
    </section>
  );
}

function SortableCard({ task, isOwner, onClick, onArchive }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 };
  const prio = (task.priority || "").toLowerCase();
  return (
    <article ref={setNodeRef} style={style} {...attributes} {...listeners}
      className={`card card-${task.column_name}`} onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}>
      <button className="card-archive" title="Archivar"
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => { e.stopPropagation(); onArchive(); }}>✓</button>
      <p className="card-text">{task.text}</p>
      <div className="card-meta">
        {task.priority && <span className={`prio prio-${prio}`}>{prioLabel(task.priority)}</span>}
        {task.tags?.map((t) => <span className="chip" key={t}>{t}</span>)}
        {task.due_date && <span className="due">📅 {task.due_date}</span>}
        {!isOwner && <span className="shared" title="De otro usuario">👤</span>}
      </div>
    </article>
  );
}

function ArchiveList({ items, onRestore, onDelete }) {
  if (!items.length) return <div className="empty">Aún no hay tareas archivadas. Marca una tarea como ✓ para archivarla.</div>;
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

function ThemePicker() {
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => document.documentElement.dataset.appTheme || "nocturne");
  function pick(id) {
    setTheme(id);
    document.documentElement.dataset.appTheme = id;
    localStorage.setItem("kanban.theme", id);
  }
  return (
    <div className="theme-picker">
      <button className="ghost" onClick={() => setOpen((o) => !o)} title="Tema" aria-label="Tema">🌗</button>
      {open && (
        <div className="theme-panel" onMouseLeave={() => setOpen(false)}>
          {THEMES.map((t) => (
            <button key={t.id} className={`theme-opt${theme === t.id ? " active" : ""}`} onClick={() => pick(t.id)}>
              <span className="chips">{t.chips.map((c, i) => <span key={i} style={{ background: c }} />)}</span>
              <span className="name">{t.name}<small>{t.sub}</small></span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PushToggle({ onError }) {
  const [enabled, setEnabled] = useState(false);
  const [supported] = useState(pushSupported());

  useEffect(() => { isPushEnabled().then(setEnabled).catch(() => {}); }, []);

  async function toggle() {
    try {
      if (enabled) { await disablePush(); setEnabled(false); }
      else { await enablePush(); setEnabled(true); }
    } catch (err) { onError(err.message); }
  }
  if (!supported) return null;
  return (
    <button className="ghost" onClick={toggle} title={enabled ? "Notificaciones activadas" : "Activar notificaciones"}>
      {enabled ? "🔔" : "🔕"}
    </button>
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
              const sel = (b.id === "default" && value.type === "default") || (value.type === "preset" && value.value === b.id);
              return (
                <button key={b.id} className={`bg-swatch${sel ? " active" : ""}`} style={{ background: b.preview }}
                  title={b.id} aria-label={b.id}
                  onClick={() => onChange(b.id === "default" ? { type: "default" } : { type: "preset", value: b.id })} />
              );
            })}
          </div>
          <label className="bg-custom">
            <span>Color personalizado</span>
            <input type="color" value={value.type === "color" ? value.value : "#0d1017"}
              onChange={(e) => onChange({ type: "color", value: e.target.value })} />
          </label>
        </div>
      )}
    </div>
  );
}

function prioLabel(p) { return { High: "Alta", Medium: "Media", Low: "Baja" }[p] || p; }
