import { useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

export default function AiPlanModal({ boardId, onClose, onDone, onError }) {
  const { t } = useT();
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (idea.trim().length < 3) return;
    setBusy(true);
    try {
      const { created } = await api.aiPlan(boardId, idea.trim());
      onDone(created);
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit}>
          <header className="modal-head">
            <h3>{t("ai.title")}</h3>
            <button type="button" className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
          </header>
          <p className="sub" style={{ margin: "0 0 14px" }}>{t("ai.desc")}</p>
          <textarea value={idea} onChange={(e) => setIdea(e.target.value)} rows={4}
            placeholder={t("ai.placeholder")} autoFocus disabled={busy} />
          <div className="modal-foot">
            <div className="spacer" />
            <button type="button" className="ghost" onClick={onClose} disabled={busy}>{t("common.cancel")}</button>
            <button type="submit" className="primary" disabled={busy}>
              {busy ? t("ai.generating") : t("ai.generate")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
