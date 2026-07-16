import { useEffect, useState } from "react";
import { api } from "./api.js";

const PRIORITIES = [["High", "Alta"], ["Medium", "Media"], ["Low", "Baja"]];
const COLS = { ToDo: "Por hacer", Doing: "En curso", Done: "Hecho" };
const VERBS = { created: "creó", edited: "editó", moved: "movió a", archived: "archivó", restored: "restauró", deleted: "eliminó" };

export default function TaskModal({ task, users, currentUser, canDelete, canArchive, onClose, onSave, onDelete, onArchive }) {
  const isNew = task.id == null;
  const [form, setForm] = useState({
    text: task.text || "",
    description: task.description || "",
    priority: task.priority || "Medium",
    tags: (task.tags || []).join(", "),
    due_date: task.due_date || "",
    column_name: task.column_name || "ToDo",
    assignee_id: task.assignee_id ?? ""
  });
  const [detail, setDetail] = useState(null);
  const [newSub, setNewSub] = useState("");
  const [newComment, setNewComment] = useState("");

  const people = [{ id: currentUser.id, username: currentUser.username }, ...users];

  const refresh = () => {
    if (!isNew) api.taskDetail(task.id).then(setDetail).catch(() => {});
  };
  useEffect(refresh, [isNew, task.id]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  function submit(e) {
    e.preventDefault();
    if (!form.text.trim()) return;
    onSave({
      ...form,
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      assignee_id: form.assignee_id === "" ? null : Number(form.assignee_id)
    }, task.id);
  }

  async function addSub() {
    if (!newSub.trim()) return;
    await api.addSubtask(task.id, newSub.trim());
    setNewSub("");
    refresh();
  }
  async function toggleSub(s) { await api.updateSubtask(s.id, { done: !s.done }); refresh(); }
  async function delSub(s) { await api.deleteSubtask(s.id); refresh(); }
  async function addCmt() {
    if (!newComment.trim()) return;
    await api.addComment(task.id, newComment.trim());
    setNewComment("");
    refresh();
  }
  async function delCmt(cid) { await api.deleteComment(cid); refresh(); }

  const subs = detail?.subtasks || [];
  const doneCount = subs.filter((s) => s.done).length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h3>{isNew ? "Nueva tarea" : "Detalle de tarea"}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">✕</button>
        </header>

        <form onSubmit={submit}>
          <label>Título</label>
          <input value={form.text} onChange={(e) => set("text", e.target.value)} placeholder="¿Qué hay que hacer?" autoFocus required />

          <label>Descripción</label>
          <textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={3} placeholder="Detalles opcionales…" />

          <div className="row-2">
            <div>
              <label>Prioridad</label>
              <select value={form.priority} onChange={(e) => set("priority", e.target.value)}>
                {PRIORITIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label>Columna</label>
              <select value={form.column_name} onChange={(e) => set("column_name", e.target.value)}>
                {Object.entries(COLS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
          </div>

          <div className="row-2">
            <div>
              <label>Asignar a</label>
              <select value={form.assignee_id} onChange={(e) => set("assignee_id", e.target.value)}>
                <option value="">Sin asignar</option>
                {people.map((u) => <option key={u.id} value={u.id}>@{u.username}</option>)}
              </select>
            </div>
            <div>
              <label>Fecha límite</label>
              <input type="date" value={form.due_date} onChange={(e) => set("due_date", e.target.value)} />
            </div>
          </div>

          <label>Etiquetas</label>
          <input value={form.tags} onChange={(e) => set("tags", e.target.value)} placeholder="casa, urgente" />

          <div className="modal-foot">
            {canDelete && <button type="button" className="danger" onClick={() => onDelete(task.id)}>Eliminar</button>}
            {canArchive && <button type="button" className="ghost" onClick={() => onArchive(task.id)}>Archivar</button>}
            <div className="spacer" />
            <button type="button" className="ghost" onClick={onClose}>Cancelar</button>
            <button type="submit" className="primary">{isNew ? "Crear" : "Guardar"}</button>
          </div>
        </form>

        {!isNew && detail && (
          <div className="detail-extra">
            {/* Subtasks */}
            <section className="detail-block">
              <h4>Subtareas {subs.length > 0 && <span className="prog">{doneCount}/{subs.length}</span>}</h4>
              {subs.length > 0 && (
                <div className="prog-bar"><span style={{ width: `${(doneCount / subs.length) * 100}%` }} /></div>
              )}
              <ul className="sub-list">
                {subs.map((s) => (
                  <li key={s.id}>
                    <label className="check">
                      <input type="checkbox" checked={s.done} onChange={() => toggleSub(s)} />
                      <span className={s.done ? "done" : ""}>{s.text}</span>
                    </label>
                    <button className="icon-btn sm" onClick={() => delSub(s)} aria-label="Eliminar">✕</button>
                  </li>
                ))}
              </ul>
              <div className="inline-add">
                <input value={newSub} onChange={(e) => setNewSub(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSub())}
                  placeholder="Añadir subtarea…" />
                <button className="ghost" onClick={addSub}>Añadir</button>
              </div>
            </section>

            {/* Comments */}
            <section className="detail-block">
              <h4>Comentarios {detail.comments.length > 0 && <span className="prog">{detail.comments.length}</span>}</h4>
              <div className="cmt-list">
                {detail.comments.map((c) => (
                  <div className="cmt" key={c.id}>
                    <div className="cmt-head">
                      <strong>@{c.username}</strong>
                      <span className="cmt-time">{(c.created_at || "").replace("T", " ").slice(0, 16)}</span>
                      {(c.username === currentUser.username) && (
                        <button className="icon-btn sm" onClick={() => delCmt(c.id)} aria-label="Eliminar">✕</button>
                      )}
                    </div>
                    <p>{c.body}</p>
                  </div>
                ))}
                {detail.comments.length === 0 && <p className="muted-note">Sé el primero en comentar.</p>}
              </div>
              <div className="inline-add">
                <input value={newComment} onChange={(e) => setNewComment(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCmt())}
                  placeholder="Escribe un comentario…" />
                <button className="ghost" onClick={addCmt}>Enviar</button>
              </div>
            </section>

            {/* Activity */}
            {detail.activity.length > 0 && (
              <details className="detail-block">
                <summary>Actividad ({detail.activity.length})</summary>
                <ul className="act-mini">
                  {detail.activity.map((a, i) => (
                    <li key={i}>
                      <strong>@{a.username}</strong> {VERBS[a.action] || a.action}
                      {a.detail && <span> {COLS[a.detail] || a.detail}</span>}
                      <span className="act-time"> · {(a.created_at || "").replace("T", " ").slice(0, 16)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
