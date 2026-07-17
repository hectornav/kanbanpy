import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

const COLORS = ["#5b8cff", "#3ecf8e", "#f0a43a", "#e5484d", "#8b5cf6", "#e0658a"];

export default function BoardSettingsModal({ board, users, onClose, onSaved, onDeleted, onError }) {
  const { t } = useT();
  const isNew = !!board.isNew;
  const [name, setName] = useState(board.name || "");
  const [color, setColor] = useState(board.color || COLORS[0]);
  const [isShared, setIsShared] = useState(!!board.is_shared);
  const [memberIds, setMemberIds] = useState([]);

  useEffect(() => {
    if (!isNew && board.id) {
      api.boardMembers(board.id).then((r) => setMemberIds(r.member_ids)).catch(() => {});
    }
  }, [isNew, board.id]);

  function toggleMember(uid) {
    setMemberIds((ids) => (ids.includes(uid) ? ids.filter((i) => i !== uid) : [...ids, uid]));
  }

  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      if (isNew) {
        const { id } = await api.createBoard({ name: name.trim(), color });
        onSaved(id);
      } else {
        await api.updateBoard(board.id, { name: name.trim(), color, is_shared: isShared, member_ids: memberIds });
        onSaved();
      }
    } catch (err) {
      onError(err.message);
    }
  }

  async function remove() {
    if (!confirm(t("bs.confirmDelete", { name: board.name }))) return;
    try {
      await api.deleteBoard(board.id);
      onDeleted();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit}>
          <header className="modal-head">
            <h3>{isNew ? t("bs.newBoard") : t("bs.settings")}</h3>
            <button type="button" className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
          </header>

          <label>{t("bs.name")}</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("bs.namePh")} autoFocus required />

          <label>{t("bs.color")}</label>
          <div className="color-row">
            {COLORS.map((c) => (
              <button
                type="button"
                key={c}
                className={`color-dot${color === c ? " active" : ""}`}
                style={{ background: c }}
                onClick={() => setColor(c)}
                aria-label={c}
              />
            ))}
          </div>

          {!isNew && (
            <>
              <label className="check">
                <input type="checkbox" checked={isShared} onChange={(e) => setIsShared(e.target.checked)} />
                {t("bs.shareAll")}
              </label>

              {!isShared && users.length > 0 && (
                <details className="share-box" open>
                  <summary>{t("bs.shareSpecific")} ({memberIds.length})</summary>
                  <div className="share-list">
                    {users.map((u) => (
                      <label key={u.id} className="check">
                        <input type="checkbox" checked={memberIds.includes(u.id)} onChange={() => toggleMember(u.id)} />
                        @{u.username}
                      </label>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}

          <footer className="modal-foot">
            {!isNew && (
              <button type="button" className="danger" onClick={remove}>{t("bs.deleteBoard")}</button>
            )}
            <div className="spacer" />
            <button type="button" className="ghost" onClick={onClose}>{t("common.cancel")}</button>
            <button type="submit" className="primary">{isNew ? t("common.create") : t("common.save")}</button>
          </footer>
        </form>
      </div>
    </div>
  );
}
