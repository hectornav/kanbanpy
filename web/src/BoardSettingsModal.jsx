import { useEffect, useState } from "react";
import { api } from "./api.js";

const COLORS = ["#5b8cff", "#3ecf8e", "#f0a43a", "#e5484d", "#8b5cf6", "#e0658a"];

export default function BoardSettingsModal({ board, users, onClose, onSaved, onDeleted, onError }) {
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
    if (!confirm(`¿Eliminar el tablero "${board.name}" y todas sus tareas?`)) return;
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
            <h3>{isNew ? "Nuevo tablero" : "Ajustes del tablero"}</h3>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">✕</button>
          </header>

          <label>Nombre</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Casa, Trabajo, Viaje…" autoFocus required />

          <label>Color</label>
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
                Compartir con todos los usuarios
              </label>

              {!isShared && users.length > 0 && (
                <details className="share-box" open>
                  <summary>Compartir con usuarios concretos ({memberIds.length})</summary>
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
              <button type="button" className="danger" onClick={remove}>Eliminar tablero</button>
            )}
            <div className="spacer" />
            <button type="button" className="ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="primary">{isNew ? "Crear" : "Guardar"}</button>
          </footer>
        </form>
      </div>
    </div>
  );
}
