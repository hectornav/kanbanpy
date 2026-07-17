import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

const VERB_KEY = {
  created: "act.created", edited: "act.edited", moved: "act.moved",
  archived: "act.archived", restored: "act.restored", deleted: "act.deleted"
};

const ICONS = {
  created: "➕", edited: "✏️", moved: "➡️", archived: "📦", restored: "♻️", deleted: "🗑️"
};

const COL_KEYS = ["ToDo", "Doing", "Done"];

export default function ActivityPanel({ boardId, boardName, onClose }) {
  const { t } = useT();
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    api.boardActivity(boardId).then(setEntries).catch(() => setEntries([]));
  }, [boardId]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <header className="drawer-head">
          <div>
            <h3>{t("act.title")}</h3>
            <p className="sub">{boardName}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
        </header>
        <div className="drawer-body">
          {entries === null && <p className="empty">{t("common.loading")}</p>}
          {entries?.length === 0 && <p className="empty">{t("act.empty")}</p>}
          {entries?.map((e, i) => (
            <div className="act-row" key={i}>
              <span className="act-icon">{ICONS[e.action] || "•"}</span>
              <div className="act-body">
                <p>
                  <strong>@{e.username}</strong> {t(VERB_KEY[e.action] || e.action)}
                  {e.detail && <span className="act-detail"> {COL_KEYS.includes(e.detail) ? t(`col.${e.detail}`) : e.detail}</span>}
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
