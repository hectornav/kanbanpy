import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

export default function AiPlanModal({ boardId, onClose, onDone, onError }) {
  const { t } = useT();
  const [cfg, setCfg] = useState(null);
  const [mode, setMode] = useState("generate"); // generate | config
  const [form, setForm] = useState({
    provider: "anthropic", anthropic_api_key: "", anthropic_model: "",
    ollama_url: "", ollama_model: ""
  });
  const [idea, setIdea] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.aiConfig().then((c) => {
      setCfg(c);
      setForm({
        provider: c.provider, anthropic_api_key: "", anthropic_model: c.anthropic_model || "",
        ollama_url: c.ollama_url || "", ollama_model: c.ollama_model || ""
      });
      setMode(c.enabled ? "generate" : "config");
    }).catch((err) => onError(err.message));
  }, [onError]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  async function saveConfig(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.saveAiConfig(form);
      const c = await api.aiConfig();
      setCfg(c);
      if (c.enabled) setMode("generate");
    } catch (err) { onError(err.message); } finally { setBusy(false); }
  }

  async function generate(e) {
    e.preventDefault();
    if (idea.trim().length < 3) return;
    setBusy(true);
    try {
      const { created } = await api.aiPlan(boardId, idea.trim());
      onDone(created);
    } catch (err) { onError(err.message); } finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h3>{t("ai.title")}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
        </header>

        {!cfg && <div className="ai-help"><p className="sub">{t("common.loading")}</p></div>}

        {cfg && mode === "generate" && (
          <form onSubmit={generate}>
            <p className="sub" style={{ margin: "0 0 14px" }}>{t("ai.desc")}</p>
            <textarea value={idea} onChange={(e) => setIdea(e.target.value)} rows={4}
              placeholder={t("ai.placeholder")} autoFocus disabled={busy} />
            <div className="modal-foot">
              {cfg.can_edit && (
                <button type="button" className="link" onClick={() => setMode("config")}>{t("ai.configure")}</button>
              )}
              <div className="spacer" />
              <button type="button" className="ghost" onClick={onClose} disabled={busy}>{t("common.cancel")}</button>
              <button type="submit" className="primary" disabled={busy}>{busy ? t("ai.generating") : t("ai.generate")}</button>
            </div>
          </form>
        )}

        {cfg && mode === "config" && !cfg.can_edit && (
          <div className="ai-help">
            <p className="sub">{t("ai.noEdit")}</p>
            <div className="modal-foot"><div className="spacer" /><button className="primary" onClick={onClose}>{t("common.cancel")}</button></div>
          </div>
        )}

        {cfg && mode === "config" && cfg.can_edit && (
          <form onSubmit={saveConfig}>
            <p className="sub" style={{ margin: "0 0 14px" }}>{t("ai.cfgIntro")}</p>

            <label>{t("ai.provider")}</label>
            <select value={form.provider} onChange={(e) => set("provider", e.target.value)}>
              <option value="anthropic">{t("ai.claude")}</option>
              <option value="ollama">{t("ai.ollamaOpt")}</option>
            </select>

            {form.provider === "anthropic" ? (
              <>
                <label>{t("ai.apiKey")} {cfg.anthropic_key_set && <span className="ok-tag">{t("ai.keySet")}</span>}</label>
                <input type="password" value={form.anthropic_api_key} autoComplete="off"
                  onChange={(e) => set("anthropic_api_key", e.target.value)} placeholder={t("ai.apiKeyPh")} />
                <label>{t("ai.model")}</label>
                <input value={form.anthropic_model} onChange={(e) => set("anthropic_model", e.target.value)}
                  placeholder="claude-opus-4-8" />
              </>
            ) : (
              <>
                <label>{t("ai.serverUrl")}</label>
                <input value={form.ollama_url} onChange={(e) => set("ollama_url", e.target.value)}
                  placeholder="http://host.docker.internal:11434" />
                <label>{t("ai.model")}</label>
                <input value={form.ollama_model} onChange={(e) => set("ollama_model", e.target.value)}
                  placeholder="llama3.1" />
              </>
            )}

            <div className="modal-foot">
              <div className="spacer" />
              <button type="button" className="ghost" onClick={onClose} disabled={busy}>{t("common.cancel")}</button>
              <button type="submit" className="primary" disabled={busy}>{busy ? "…" : t("common.save")}</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
