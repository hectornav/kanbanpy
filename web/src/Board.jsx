import { useCallback, useEffect, useState } from "react";
import {
  DndContext, PointerSensor, TouchSensor, useSensor, useSensors, closestCorners, useDroppable
} from "@dnd-kit/core";
import {
  SortableContext, useSortable, arrayMove, verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, connectLiveSync, flushQueue, offline } from "./api.js";
import { enablePush, disablePush, isPushEnabled, pushSupported } from "./push.js";
import { useT, LANGS } from "./i18n.jsx";
import TaskModal from "./TaskModal.jsx";
import BoardSettingsModal from "./BoardSettingsModal.jsx";
import ActivityPanel from "./ActivityPanel.jsx";
import AiPlanModal from "./AiPlanModal.jsx";

const COLUMNS = [
  { key: "ToDo", accent: "var(--todo)" },
  { key: "Doing", accent: "var(--doing)" },
  { key: "Done", accent: "var(--done)" }
];
const COLUMN_KEYS = COLUMNS.map((c) => c.key);

const THEMES = [
  { id: "nocturne", chips: ["#0d1017", "#6d8bff", "#37d69f"] },
  { id: "frost", chips: ["#eef1f6", "#2f5fe0", "#0a9d5f"] },
  { id: "meridian", chips: ["#131110", "#ff8a5c", "#4fd6b0"] }
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
  const { t } = useT();
  const [boards, setBoards] = useState([]);
  const [activeId, setActiveId] = useState(() => Number(localStorage.getItem("kanban.board")) || null);
  const [board, setBoard] = useState({ ToDo: [], Doing: [], Done: [] });
  const [archived, setArchived] = useState([]);
  const [view, setView] = useState("board");
  const [users, setUsers] = useState([]);
  const [editing, setEditing] = useState(null);
  const [settingsFor, setSettingsFor] = useState(null);
  const [showActivity, setShowActivity] = useState(false);
  const [showAi, setShowAi] = useState(false);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [online, setOnline] = useState(offline.isOnline());
  const [pending, setPending] = useState(offline.queueSize());
  const [bg, setBg] = useState(readBg);
  const [query, setQuery] = useState("");
  const [fPrio, setFPrio] = useState("");
  const [fAssignee, setFAssignee] = useState("");

  const active = boards.find((b) => b.id === activeId) || null;
  const filtering = !!(query || fPrio || fAssignee);

  function matches(t) {
    if (query && !`${t.text} ${t.description} ${(t.tags || []).join(" ")}`.toLowerCase().includes(query.toLowerCase()))
      return false;
    if (fPrio && t.priority !== fPrio) return false;
    if (fAssignee && String(t.assignee_id ?? "") !== fAssignee) return false;
    return true;
  }

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
    api.aiStatus().then((s) => setAiEnabled(s.enabled)).catch(() => {});
  }, [loadBoards]);

  useEffect(() => {
    loadTasks();
    const disconnect = connectLiveSync(() => { loadTasks(); loadBoards(); });
    return disconnect;
  }, [loadTasks, loadBoards]);

  useEffect(() => {
    if (activeId) localStorage.setItem("kanban.board", String(activeId));
  }, [activeId]);

  // Online/offline handling: flush queued mutations when the network returns.
  useEffect(() => {
    async function goOnline() {
      setOnline(true);
      if (offline.queueSize() > 0) {
        setNotice(t("offline.syncing"));
        await flushQueue().catch(() => {});
        setPending(offline.queueSize());
        await loadBoards();
        await loadTasks();
      }
    }
    function goOffline() {
      setOnline(false);
      setPending(offline.queueSize());
    }
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, [t, loadBoards, loadTasks]);

  // Optimistically reflect an offline change locally (the queue syncs on reconnect).
  function localCreate(data) {
    const task = {
      id: -Date.now(), owner_id: user.id, ...data,
      subtask_total: 0, subtask_done: 0, comment_count: 0
    };
    const col = data.column_name || "ToDo";
    setBoard((prev) => ({ ...prev, [col]: [...(prev[col] || []), task] }));
  }
  function localEdit(id, data) {
    setBoard((prev) => {
      const next = { ToDo: [], Doing: [], Done: [] };
      for (const k of COLUMN_KEYS) next[k] = (prev[k] || []).filter((t) => t.id !== id);
      const merged = { id, owner_id: user.id, ...data };
      const col = data.column_name || "ToDo";
      next[col] = [...next[col], merged];
      return next;
    });
  }

  async function handleSave(data, id) {
    try {
      const res = id ? await api.updateTask(id, data) : await api.createTask(activeId, data);
      setEditing(null);
      if (res?.queued) {
        id ? localEdit(id, data) : localCreate(data);
        setPending(offline.queueSize());
      } else {
        await loadTasks();
      }
    } catch (err) { setError(err.message); }
  }

  async function act(promise) {
    try {
      await promise;
      setEditing(null);
      await loadTasks();
      setPending(offline.queueSize());
    } catch (err) { setError(err.message); }
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
    ).then(() => setPending(offline.queueSize())).catch((e) => { setError(e.message); loadTasks(); });
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
          <button className="ghost" onClick={() => setShowActivity(true)} title={t("nav.activity")}>🕘</button>
          <LanguagePicker />
          <ThemePicker />
          <BackgroundPicker value={bg} onChange={changeBg} />
          <button className="ghost" onClick={onLogout}>{t("common.logout")}</button>
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
        <button className="tab add" onClick={() => setSettingsFor({ isNew: true })}>{t("nav.newBoard")}</button>
      </nav>

      {!online && (
        <div className="banner warn-banner">
          {t("offline.title")}{pending > 0 ? " " + t("offline.pending", { n: pending }) : ""}
        </div>
      )}
      {error && <div className="banner" onClick={() => setError("")}>{error} · {t("board.closeBanner")}</div>}
      {notice && <div className="banner ok-banner" onClick={() => setNotice("")}>{notice}</div>}

      <div className="board-bar">
        <div className="seg">
          <button className={view === "board" ? "on" : ""} onClick={() => setView("board")}>{t("nav.board")}</button>
          <button className={view === "list" ? "on" : ""} onClick={() => setView("list")}>{t("nav.list")}</button>
          <button className={view === "calendar" ? "on" : ""} onClick={() => setView("calendar")}>{t("nav.calendar")}</button>
          <button className={view === "archive" ? "on" : ""} onClick={() => setView("archive")}>{t("nav.archive")}</button>
        </div>
        <div className="board-bar-right">
          {view !== "archive" && <button className="ghost" onClick={() => setShowAi(true)}>{t("ai.button")}</button>}
          {view === "board" && <button className="ghost" onClick={() => setEditing({ column_name: "ToDo" })}>{t("nav.newTask")}</button>}
          {active?.is_owner && <button className="ghost" onClick={() => setSettingsFor({ ...active })} title={t("nav.boardSettings")}>⚙️</button>}
        </div>
      </div>

      {view !== "archive" && (
        <div className="filter-bar">
          <input className="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("board.searchPh")} />
          <select value={fPrio} onChange={(e) => setFPrio(e.target.value)}>
            <option value="">{t("board.prioAll")}</option>
            <option value="High">{t("prio.High")}</option>
            <option value="Medium">{t("prio.Medium")}</option>
            <option value="Low">{t("prio.Low")}</option>
          </select>
          <select value={fAssignee} onChange={(e) => setFAssignee(e.target.value)}>
            <option value="">{t("board.assigneeAll")}</option>
            <option value={String(user.id)}>@{user.username} {t("board.me")}</option>
            {users.map((u) => <option key={u.id} value={String(u.id)}>@{u.username}</option>)}
          </select>
          {filtering && <button className="link" onClick={() => { setQuery(""); setFPrio(""); setFAssignee(""); }}>{t("common.clear")}</button>}
        </div>
      )}

      <div className="board-scroll" style={view === "board" ? bgStyle(bg) : undefined}>
        {view === "board" ? (
          <DndContext sensors={sensors} collisionDetection={closestCorners} onDragOver={onDragOver} onDragEnd={onDragEnd}>
            <div className="board-grid">
              {COLUMNS.map((col) => (
                <Column key={col.key} col={col} tasks={board[col.key] || []}
                  currentUserId={user.id} matches={matches}
                  onAdd={() => setEditing({ column_name: col.key })}
                  onOpen={setEditing}
                  onArchive={(id) => act(api.archiveTask(id))} />
              ))}
            </div>
          </DndContext>
        ) : view === "list" ? (
          <ListView board={board} matches={matches} onOpen={setEditing} />
        ) : view === "calendar" ? (
          <CalendarView board={board} matches={matches} onOpen={setEditing} />
        ) : (
          <ArchiveList items={archived} onRestore={(id) => act(api.restoreTask(id))} onDelete={(id) => act(api.deleteTask(id))} />
        )}
      </div>

      {editing && (
        <TaskModal task={editing} users={users} currentUser={user}
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
      {showAi && activeId && (
        <AiPlanModal boardId={activeId} enabled={aiEnabled}
          onClose={() => setShowAi(false)}
          onError={(m) => { setShowAi(false); setError(m); }}
          onDone={async (n) => { setShowAi(false); setNotice(t("ai.created", { n })); await loadTasks(); }} />
      )}
    </div>
  );
}

function Column({ col, tasks, currentUserId, matches, onAdd, onOpen, onArchive }) {
  const { t } = useT();
  const { setNodeRef, isOver } = useDroppable({ id: col.key });
  const visibleCount = tasks.filter(matches).length;
  return (
    <section className="board-col">
      <div className="col-head" style={{ "--accent": col.accent }}>
        <span className="col-title">{t(`col.${col.key}`)}</span>
        <span className="col-count">{visibleCount}</span>
      </div>
      <SortableContext items={tasks.map((t2) => t2.id)} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className={`col-body${isOver ? " drop-over" : ""}`}>
          {tasks.map((task) => (
            <SortableCard key={task.id} task={task} hidden={!matches(task)}
              isOwner={task.owner_id === currentUserId}
              onClick={() => onOpen(task)} onArchive={() => onArchive(task.id)} />
          ))}
          <button className="add-inline" onClick={onAdd}>{t("board.addInline")}</button>
        </div>
      </SortableContext>
    </section>
  );
}

function initials(name) {
  return (name || "?").slice(0, 2).toUpperCase();
}
function avatarColor(name) {
  const palette = ["#e0658a", "#5b8cff", "#3ecf8e", "#f0a43a", "#8b5cf6", "#ff8a5c"];
  let h = 0;
  for (const ch of name || "") h = (h + ch.charCodeAt(0)) % palette.length;
  return palette[h];
}

function SortableCard({ task, hidden, isOwner, onClick, onArchive }) {
  const { t } = useT();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 };
  const prio = (task.priority || "").toLowerCase();
  return (
    <article ref={setNodeRef} style={style} {...attributes} {...listeners}
      className={`card card-${task.column_name}${hidden ? " card-hidden" : ""}`} onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}>
      <button className="card-archive" title={t("common.archive")}
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => { e.stopPropagation(); onArchive(); }}>✓</button>
      <p className="card-text">{task.text}</p>
      <div className="card-meta">
        {task.priority && <span className={`prio prio-${prio}`}>{t(`prio.${task.priority}`)}</span>}
        {task.subtask_total > 0 && (
          <span className="badge-mini" title="Subtareas">☑ {task.subtask_done}/{task.subtask_total}</span>
        )}
        {task.comment_count > 0 && <span className="badge-mini" title="Comentarios">💬 {task.comment_count}</span>}
        {task.recurrence && <span className="badge-mini" title={t(`rec.${task.recurrence}`)}>🔁</span>}
        {task.tags?.map((tg) => <span className="chip" key={tg}>{tg}</span>)}
        {task.due_date && <span className="due">📅 {task.due_date}</span>}
        {task.assignee_username && (
          <span className="avatar" style={{ background: avatarColor(task.assignee_username) }} title={`@${task.assignee_username}`}>
            {initials(task.assignee_username)}
          </span>
        )}
      </div>
    </article>
  );
}

function ArchiveList({ items, onRestore, onDelete }) {
  const { t } = useT();
  if (!items.length) return <div className="empty">{t("board.emptyArchive")}</div>;
  return (
    <div className="archive-list">
      {items.map((it) => (
        <div className="archive-row" key={it.id}>
          <div className="archive-main">
            <span className={`dot dot-${it.column_name}`} />
            <span className="archive-text">{it.text}</span>
            {it.archived_at && <span className="archive-date">{t("board.archivedOn")} {it.archived_at.slice(0, 10)}</span>}
          </div>
          <div className="archive-actions">
            <button className="ghost" onClick={() => onRestore(it.id)}>{t("common.restore")}</button>
            <button className="danger" onClick={() => onDelete(it.id)}>{t("common.delete")}</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function ListView({ board, matches, onOpen }) {
  const { t } = useT();
  const groups = COLUMNS.map((col) => ({ col, items: (board[col.key] || []).filter(matches) }))
    .filter((g) => g.items.length);
  if (!groups.length) return <div className="empty">{t("board.noMatch")}</div>;
  return (
    <div className="list-view">
      {groups.map(({ col, items }) => (
        <div className="list-group" key={col.key}>
          <div className="list-group-h"><span className="dot" style={{ background: col.accent }} />{t(`col.${col.key}`)}<span className="count">{items.length}</span></div>
          {items.map((it) => (
            <button className="list-row" key={it.id} onClick={() => onOpen(it)}>
              <span className="list-text">{it.text}</span>
              <span className="list-meta">
                {it.priority && <span className={`prio prio-${it.priority.toLowerCase()}`}>{t(`prio.${it.priority}`)}</span>}
                {it.subtask_total > 0 && <span className="badge-mini">☑ {it.subtask_done}/{it.subtask_total}</span>}
                {it.comment_count > 0 && <span className="badge-mini">💬 {it.comment_count}</span>}
                {it.recurrence && <span className="badge-mini" title={t(`rec.${it.recurrence}`)}>🔁</span>}
                {it.due_date && <span className="due">📅 {it.due_date}</span>}
                {it.assignee_username && <span className="avatar" style={{ background: avatarColor(it.assignee_username) }}>{initials(it.assignee_username)}</span>}
              </span>
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}

const WEEKDAYS = {
  es: ["L", "M", "X", "J", "V", "S", "D"],
  ca: ["Dl", "Dt", "Dc", "Dj", "Dv", "Ds", "Dg"],
  en: ["M", "T", "W", "T", "F", "S", "S"]
};
const LOCALES = { es: "es-ES", ca: "ca-ES", en: "en-GB" };
const pad2 = (n) => String(n).padStart(2, "0");

function CalendarView({ board, matches, onOpen }) {
  const { t, lang } = useT();
  const today = new Date();
  const [cur, setCur] = useState({ y: today.getFullYear(), m: today.getMonth() });

  const all = [...board.ToDo, ...board.Doing, ...board.Done].filter(matches);
  const byDate = {};
  const noDate = [];
  for (const tk of all) {
    if (tk.due_date) (byDate[tk.due_date] ||= []).push(tk);
    else noDate.push(tk);
  }

  const first = new Date(cur.y, cur.m, 1);
  const startDow = (first.getDay() + 6) % 7; // Monday-first
  const daysInMonth = new Date(cur.y, cur.m + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  const title = first.toLocaleDateString(LOCALES[lang] || "es-ES", { month: "long", year: "numeric" });
  const dayKey = (d) => `${cur.y}-${pad2(cur.m + 1)}-${pad2(d)}`;
  const todayKey = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`;
  const shift = (n) => setCur(({ y, m }) => { const d = new Date(y, m + n, 1); return { y: d.getFullYear(), m: d.getMonth() }; });

  return (
    <div className="cal">
      <div className="cal-head">
        <button className="ghost" onClick={() => shift(-1)}>‹</button>
        <span className="cal-title">{title}</span>
        <button className="ghost" onClick={() => shift(1)}>›</button>
        <button className="ghost" onClick={() => setCur({ y: today.getFullYear(), m: today.getMonth() })}>{t("cal.today")}</button>
      </div>
      <div className="cal-grid cal-dow">{(WEEKDAYS[lang] || WEEKDAYS.es).map((d, i) => <div key={i} className="cal-dow-cell">{d}</div>)}</div>
      <div className="cal-grid">
        {cells.map((d, i) => (
          <div key={i} className={`cal-cell${d ? "" : " empty-cell"}${d && dayKey(d) === todayKey ? " today" : ""}`}>
            {d && <span className="cal-day">{d}</span>}
            {d && (byDate[dayKey(d)] || []).map((tk) => (
              <button key={tk.id} className={`cal-task cal-${tk.column_name}`} onClick={() => onOpen(tk)} title={tk.text}>{tk.text}</button>
            ))}
          </div>
        ))}
      </div>
      {noDate.length > 0 && (
        <div className="cal-nodate">
          <span className="lbl">{t("cal.noDate")}</span>
          {noDate.map((tk) => (
            <button key={tk.id} className={`cal-task cal-${tk.column_name}`} onClick={() => onOpen(tk)}>{tk.text}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function LanguagePicker() {
  const { lang, setLang } = useT();
  const [open, setOpen] = useState(false);
  return (
    <div className="theme-picker">
      <button className="ghost" onClick={() => setOpen((o) => !o)} title="Idioma" aria-label="Idioma">🌐</button>
      {open && (
        <div className="theme-panel" onMouseLeave={() => setOpen(false)}>
          {LANGS.map((l) => (
            <button key={l.id} className={`theme-opt${lang === l.id ? " active" : ""}`}
              onClick={() => { setLang(l.id); setOpen(false); }}>
              <span className="name">{l.flag} {l.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ThemePicker() {
  const { t } = useT();
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => document.documentElement.dataset.appTheme || "nocturne");
  function pick(id) {
    setTheme(id);
    document.documentElement.dataset.appTheme = id;
    localStorage.setItem("kanban.theme", id);
  }
  return (
    <div className="theme-picker">
      <button className="ghost" onClick={() => setOpen((o) => !o)} title={t("nav.theme")} aria-label={t("nav.theme")}>🌗</button>
      {open && (
        <div className="theme-panel" onMouseLeave={() => setOpen(false)}>
          {THEMES.map((th) => (
            <button key={th.id} className={`theme-opt${theme === th.id ? " active" : ""}`} onClick={() => pick(th.id)}>
              <span className="chips">{th.chips.map((c, i) => <span key={i} style={{ background: c }} />)}</span>
              <span className="name">{t(`theme.${th.id}`)}<small>{t(`theme.${th.id}Sub`)}</small></span>
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
  const { t } = useT();
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-picker">
      <button className="ghost" onClick={() => setOpen((o) => !o)} title={t("nav.background")} aria-label={t("nav.background")}>🎨</button>
      {open && (
        <div className="bg-panel" onMouseLeave={() => setOpen(false)}>
          <p className="lbl">{t("nav.background")}</p>
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
            <span>{t("board.bgCustom")}</span>
            <input type="color" value={value.type === "color" ? value.value : "#0d1017"}
              onChange={(e) => onChange({ type: "color", value: e.target.value })} />
          </label>
        </div>
      )}
    </div>
  );
}
