import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

const PRIOS = ["High", "Medium", "Low"];
const COL_KEYS = ["ToDo", "Doing", "Done"];
const VERB_KEY = { created: "act.created", edited: "act.edited", moved: "act.moved", archived: "act.archived", restored: "act.restored", deleted: "act.deleted" };

export default function TaskModal({ task, users, currentUser, canDelete, canArchive, onClose, onSave, onDelete, onArchive }) {
  const { t } = useT();
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

  const refresh = () => { if (!isNew) api.taskDetail(task.id).then(setDetail).catch(() => {}); };
  useEffect(refresh, [isNew, task.id]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  function submit(e) {
    e.preventDefault();
    if (!form.text.trim()) return;
    onSave({
      ...form,
      tags: form.tags.split(",").map((x) => x.trim()).filter(Boolean),
      assignee_id: form.assignee_id === "" ? null : Number(form.assignee_id)
    }, task.id);
  }

  async function addSub() { if (!newSub.trim()) return; await api.addSubtask(task.id, newSub.trim()); setNewSub(""); refresh(); }
  async function toggleSub(s) { await api.updateSubtask(s.id, { done: !s.done }); refresh(); }
  async function delSub(s) { await api.deleteSubtask(s.id); refresh(); }
  async function addCmt() { if (!newComment.trim()) return; await api.addComment(task.id, newComment.trim()); setNewComment(""); refresh(); }
  async function delCmt(cid) { await api.deleteComment(cid); refresh(); }

  const subs = detail?.subtasks || [];
  const doneCount = subs.filter((s) => s.done).length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h3>{isNew ? t("task.newTask") : t("task.detail")}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
        </header>

        <form onSubmit={submit}>
          <label>{t("task.title")}</label>
          <input value={form.text} onChange={(e) => set("text", e.target.value)} placeholder={t("task.titlePh")} autoFocus required />

          <label>{t("task.description")}</label>
          <textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={3} placeholder={t("task.descPh")} />

          <div className="row-2">
            <div>
              <label>{t("task.priority")}</label>
              <select value={form.priority} onChange={(e) => set("priority", e.target.value)}>
                {PRIOS.map((p) => <option key={p} value={p}>{t(`prio.${p}`)}</option>)}
              </select>
            </div>
            <div>
              <label>{t("task.column")}</label>
              <select value={form.column_name} onChange={(e) => set("column_name", e.target.value)}>
                {COL_KEYS.map((k) => <option key={k} value={k}>{t(`col.${k}`)}</option>)}
              </select>
            </div>
          </div>

          <div className="row-2">
            <div>
              <label>{t("task.assignTo")}</label>
              <select value={form.assignee_id} onChange={(e) => set("assignee_id", e.target.value)}>
                <option value="">{t("task.unassigned")}</option>
                {people.map((u) => <option key={u.id} value={u.id}>@{u.username}</option>)}
              </select>
            </div>
            <div>
              <label>{t("task.dueDate")}</label>
              <input type="date" value={form.due_date} onChange={(e) => set("due_date", e.target.value)} />
            </div>
          </div>

          <label>{t("task.tags")}</label>
          <input value={form.tags} onChange={(e) => set("tags", e.target.value)} placeholder={t("task.tagsPh")} />

          <div className="modal-foot">
            {canDelete && <button type="button" className="danger" onClick={() => onDelete(task.id)}>{t("common.delete")}</button>}
            {canArchive && <button type="button" className="ghost" onClick={() => onArchive(task.id)}>{t("common.archive")}</button>}
            <div className="spacer" />
            <button type="button" className="ghost" onClick={onClose}>{t("common.cancel")}</button>
            <button type="submit" className="primary">{isNew ? t("common.create") : t("common.save")}</button>
          </div>
        </form>

        {!isNew && detail && (
          <div className="detail-extra">
            <section className="detail-block">
              <h4>{t("task.subtasks")} {subs.length > 0 && <span className="prog">{doneCount}/{subs.length}</span>}</h4>
              {subs.length > 0 && <div className="prog-bar"><span style={{ width: `${(doneCount / subs.length) * 100}%` }} /></div>}
              <ul className="sub-list">
                {subs.map((s) => (
                  <li key={s.id}>
                    <label className="check">
                      <input type="checkbox" checked={s.done} onChange={() => toggleSub(s)} />
                      <span className={s.done ? "done" : ""}>{s.text}</span>
                    </label>
                    <button className="icon-btn sm" onClick={() => delSub(s)} aria-label={t("common.delete")}>✕</button>
                  </li>
                ))}
              </ul>
              <div className="inline-add">
                <input value={newSub} onChange={(e) => setNewSub(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSub())} placeholder={t("task.addSubtaskPh")} />
                <button className="ghost" onClick={addSub}>{t("common.add")}</button>
              </div>
            </section>

            <section className="detail-block">
              <h4>{t("task.comments")} {detail.comments.length > 0 && <span className="prog">{detail.comments.length}</span>}</h4>
              <div className="cmt-list">
                {detail.comments.map((c) => (
                  <div className="cmt" key={c.id}>
                    <div className="cmt-head">
                      <strong>@{c.username}</strong>
                      <span className="cmt-time">{(c.created_at || "").replace("T", " ").slice(0, 16)}</span>
                      {(c.username === currentUser.username) && <button className="icon-btn sm" onClick={() => delCmt(c.id)} aria-label={t("common.delete")}>✕</button>}
                    </div>
                    <p>{c.body}</p>
                  </div>
                ))}
                {detail.comments.length === 0 && <p className="muted-note">{t("task.firstComment")}</p>}
              </div>
              <div className="inline-add">
                <input value={newComment} onChange={(e) => setNewComment(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addCmt())} placeholder={t("task.commentPh")} />
                <button className="ghost" onClick={addCmt}>{t("common.send")}</button>
              </div>
            </section>

            {detail.activity.length > 0 && (
              <details className="detail-block">
                <summary>{t("task.activity")} ({detail.activity.length})</summary>
                <ul className="act-mini">
                  {detail.activity.map((a, i) => (
                    <li key={i}>
                      <strong>@{a.username}</strong> {t(VERB_KEY[a.action] || a.action)}
                      {a.detail && <span> {COL_KEYS.includes(a.detail) ? t(`col.${a.detail}`) : a.detail}</span>}
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
