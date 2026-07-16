import { useEffect, useState } from "react";
import { api } from "./api.js";

const VERBS = {
  created: "creó",
  edited: "editó",
  moved: "movió a",
  archived: "archivó",
  restored: "restauró",
  deleted: "eliminó"
};

const ICONS = {
  created: "➕",
  edited: "✏️",
  moved: "➡️",
  archived: "📦",
  restored: "♻️",
  deleted: "🗑️"
};

const COLS = { ToDo: "Por hacer", Doing: "En curso", Done: "Hecho" };

export default function ActivityPanel({ boardId, boardName, onClose }) {
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    api.boardActivity(boardId).then(setEntries).catch(() => setEntries([]));
  }, [boardId]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <h3>Actividad</h3>
            <p className="sub">{boardName}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Cerrar">✕</button>
        </header>
        <div className="drawer-body">
          {entries === null && <p className="empty">Cargando…</p>}
          {entries?.length === 0 && <p className="empty">Sin actividad todavía.</p>}
          {entries?.map((e, i) => (
            <div className="act-row" key={i}>
              <span className="act-icon">{ICONS[e.action] || "•"}</span>
              <div className="act-body">
                <p>
                  <strong>@{e.username}</strong> {VERBS[e.action] || e.action}
                  {e.detail && <span className="act-detail"> {COLS[e.detail] || e.detail}</span>}
                </p>
                <span className="act-time">{formatTime(e.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

function formatTime(iso) {
  if (!iso) return "";
  return iso.replace("T", " ").slice(0, 16);
}
