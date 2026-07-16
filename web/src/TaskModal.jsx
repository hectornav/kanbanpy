import { useEffect, useState } from "react";
import { api } from "./api.js";

const PRIORITIES = [
  ["High", "Alta"],
  ["Medium", "Media"],
  ["Low", "Baja"]
];

export default function TaskModal({ task, users, canDelete, onClose, onSave, onDelete }) {
  const isNew = task.id == null;
  const [form, setForm] = useState({
    text: task.text || "",
    description: task.description || "",
    priority: task.priority || "Medium",
    tags: (task.tags || []).join(", "),
    due_date: task.due_date || "",
    column_name: task.column_name || "ToDo",
    is_shared: !!task.is_shared
  });
  const [sharedIds, setSharedIds] = useState([]);

  // Load explicit shares when editing an existing task.
  useEffect(() => {
    if (!isNew) {
      api.taskShares(task.id).then((r) => setSharedIds(r.shared_user_ids)).catch(() => {});
    }
  }, [isNew, task.id]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function toggleShare(uid) {
    setSharedIds((ids) => (ids.includes(uid) ? ids.filter((i) => i !== uid) : [...ids, uid]));
  }

  function submit(e) {
    e.preventDefault();
    if (!form.text.trim()) return;
    onSave(
      {
        ...form,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
        shared_user_ids: sharedIds
      },
      task.id
    );
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit}>
          <header className="modal-head">
            <h3>{isNew ? "Nueva tarea" : "Editar tarea"}</h3>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">✕</button>
          </header>

          <label>Título</label>
          <input value={form.text} onChange={(e) => set("text", e.target.value)} placeholder="¿Qué hay que hacer?" autoFocus required />

          <label>Descripción</label>
          <textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={3} placeholder="Detalles opcionales…" />

          <div className="row-2">
            <div>
              <label>Prioridad</label>
              <select value={form.priority} onChange={(e) => set("priority", e.target.value)}>
                {PRIORITIES.map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label>Columna</label>
              <select value={form.column_name} onChange={(e) => set("column_name", e.target.value)}>
                <option value="ToDo">Por hacer</option>
                <option value="Doing">En curso</option>
                <option value="Done">Hecho</option>
              </select>
            </div>
          </div>

          <div className="row-2">
            <div>
              <label>Etiquetas</label>
              <input value={form.tags} onChange={(e) => set("tags", e.target.value)} placeholder="casa, urgente" />
            </div>
            <div>
              <label>Fecha límite</label>
              <input type="date" value={form.due_date} onChange={(e) => set("due_date", e.target.value)} />
            </div>
          </div>

          <label className="check">
            <input type="checkbox" checked={form.is_shared} onChange={(e) => set("is_shared", e.target.checked)} />
            Compartir con todos los usuarios
          </label>

          {!form.is_shared && users.length > 0 && (
            <details className="share-box">
              <summary>Compartir con personas concretas ({sharedIds.length})</summary>
              <div className="share-list">
                {users.map((u) => (
                  <label key={u.id} className="check">
                    <input type="checkbox" checked={sharedIds.includes(u.id)} onChange={() => toggleShare(u.id)} />
                    @{u.username}
                  </label>
                ))}
              </div>
            </details>
          )}

          <footer className="modal-foot">
            {canDelete && (
              <button type="button" className="danger" onClick={() => onDelete(task.id)}>Eliminar</button>
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
