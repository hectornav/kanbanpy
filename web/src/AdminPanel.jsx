import { useEffect, useState } from "react";
import { api } from "./api.js";
import { useT } from "./i18n.jsx";

export default function AdminPanel({ currentUserId, onClose, onError, onOrgRenamed }) {
  const { t } = useT();
  const [org, setOrg] = useState(null);
  const [members, setMembers] = useState([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      const [o, m] = await Promise.all([api.org(), api.orgMembers()]);
      setOrg(o);
      setName(o.name);
      setMembers(m);
    } catch (err) {
      onError(err.message);
      onClose();
    }
  }

  useEffect(() => { load(); }, []);

  async function saveName(e) {
    e.preventDefault();
    if (!name.trim() || name.trim() === org?.name) return;
    setBusy(true);
    try {
      const o = await api.renameOrg({ name: name.trim() });
      setOrg(o);
      setNotice(t("admin.renamed"));
      onOrgRenamed?.(o.name);
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function rotate() {
    if (!confirm(t("admin.confirmRotate"))) return;
    setBusy(true);
    try {
      const o = await api.rotateInvite();
      setOrg(o);
      setNotice(t("admin.rotated"));
      setCopied(false);
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function copyCode() {
    if (!org?.invite_code) return;
    try {
      await navigator.clipboard.writeText(org.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onError(t("admin.copyFail"));
    }
  }

  async function toggleActive(member) {
    setBusy(true);
    try {
      const updated = await api.setMemberActive(member.id, { is_active: !member.is_active });
      setMembers((list) => list.map((m) => (m.id === updated.id ? updated : m)));
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h3>{t("admin.title")}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t("common.cancel")}>✕</button>
        </header>

        {!org ? (
          <p className="empty" style={{ padding: "0 22px 22px" }}>{t("common.loading")}</p>
        ) : (
          <div className="admin-body">
            {notice && <p className="ok admin-notice">{notice}</p>}

            <form onSubmit={saveName} className="admin-section">
              <label>{t("org.name")}</label>
              <div className="admin-row">
                <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required />
                <button type="submit" className="primary" disabled={busy || name.trim() === org.name}>
                  {t("common.save")}
                </button>
              </div>
            </form>

            <div className="admin-section">
              <label>{t("org.inviteCode")}</label>
              <p className="hint">{t("admin.inviteHint")}</p>
              <div className="admin-row">
                <code className="invite-code">{org.invite_code}</code>
                <button type="button" className="ghost" onClick={copyCode} disabled={busy}>
                  {copied ? t("admin.copied") : t("admin.copy")}
                </button>
                <button type="button" className="ghost" onClick={rotate} disabled={busy}>
                  {t("admin.rotate")}
                </button>
              </div>
            </div>

            <div className="admin-section">
              <label>{t("admin.members")} ({members.length})</label>
              <p className="hint">{t("admin.membersHint")}</p>
              <ul className="admin-members">
                {members.map((m) => {
                  const isSelf = m.id === currentUserId;
                  return (
                    <li key={m.id} className={!m.is_active ? "inactive" : ""}>
                      <div className="admin-member-info">
                        <strong>@{m.username}</strong>
                        {m.is_org_admin && <span className="badge">{t("admin.badgeAdmin")}</span>}
                        {!m.is_active && <span className="badge muted">{t("admin.badgeInactive")}</span>}
                      </div>
                      <button
                        type="button"
                        className={m.is_active ? "ghost danger-text" : "ghost"}
                        disabled={busy || isSelf}
                        title={isSelf ? t("admin.cannotSelf") : undefined}
                        onClick={() => toggleActive(m)}
                      >
                        {m.is_active ? t("admin.deactivate") : t("admin.activate")}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
