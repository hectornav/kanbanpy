import { useState } from "react";
import { api, auth } from "./api.js";
import { useT, LANGS } from "./i18n.jsx";

export default function AuthScreen({ onAuthenticated }) {
  const { t, lang, setLang } = useT();
  const [mode, setMode] = useState("login"); // login | register | forgot
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [securityQ, setSecurityQ] = useState("");

  const FEATURES = [t("feat.1"), t("feat.2"), t("feat.3"), t("feat.4")];

  function reset() { setError(""); setOk(""); }

  async function handleLogin(e) {
    e.preventDefault();
    reset();
    setBusy(true);
    const f = new FormData(e.target);
    try {
      const res = await api.login({ username: f.get("username").trim(), password: f.get("password") });
      auth.token = res.access_token;
      onAuthenticated(res.user);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function handleRegister(e) {
    e.preventDefault();
    reset();
    const f = new FormData(e.target);
    if (f.get("password") !== f.get("password2")) { setError(t("auth.passMismatch")); return; }
    setBusy(true);
    try {
      await api.register({
        username: f.get("username").trim(), password: f.get("password"),
        security_q: f.get("security_q").trim(), security_a: f.get("security_a").trim()
      });
      const res = await api.login({ username: f.get("username").trim(), password: f.get("password") });
      auth.token = res.access_token;
      onAuthenticated(res.user);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function loadQuestion(username) {
    if (!username.trim()) return;
    try {
      const { security_q } = await api.securityQuestion(username.trim());
      setSecurityQ(security_q || t("auth.notFound"));
    } catch { setSecurityQ(""); }
  }

  async function handleForgot(e) {
    e.preventDefault();
    reset();
    setBusy(true);
    const f = new FormData(e.target);
    try {
      await api.resetPassword({
        username: f.get("username").trim(), answer: f.get("answer").trim(), new_password: f.get("new_password")
      });
      setOk(t("auth.resetOk"));
      setMode("login");
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  return (
    <div className="auth">
      <aside className="auth-brand">
        <span className="logo-mark">📋</span>
        <h1>{t("brand")}</h1>
        <p className="brand-tag">{t("auth.tagline")}</p>
        <ul className="brand-features">{FEATURES.map((f) => <li key={f}>✦ {f}</li>)}</ul>
      </aside>

      <main className="auth-card">
        <div className="lang-row">
          {LANGS.map((l) => (
            <button key={l.id} className={`lang-btn${lang === l.id ? " active" : ""}`} onClick={() => setLang(l.id)}>
              {l.flag} {l.id.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="auth-inner">
          {mode === "login" && (
            <form onSubmit={handleLogin} className="auth-form">
              <h2>{t("auth.welcome")}</h2>
              <p className="sub">{t("auth.loginSubtitle")}</p>
              <label>{t("auth.user")}</label>
              <input name="username" autoComplete="username" placeholder={t("auth.userPh")} required />
              <label>{t("auth.password")}</label>
              <input name="password" type="password" autoComplete="current-password" placeholder={t("auth.passwordPh")} required />
              {error && <p className="err">❌ {error}</p>}
              {ok && <p className="ok">✅ {ok}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : t("auth.login")}</button>
              <div className="switch">
                <button type="button" className="link" onClick={() => { reset(); setMode("forgot"); }}>{t("auth.forgot")}</button>
                <span>{t("auth.noAccount")}{" "}
                  <button type="button" className="link" onClick={() => { reset(); setMode("register"); }}>{t("auth.register")}</button>
                </span>
              </div>
            </form>
          )}

          {mode === "register" && (
            <form onSubmit={handleRegister} className="auth-form">
              <h2>{t("auth.createAccount")}</h2>
              <p className="sub">{t("auth.registerSubtitle")}</p>
              <label>{t("auth.user")}</label>
              <input name="username" placeholder={t("auth.chooseName")} required />
              <label>{t("auth.password")}</label>
              <input name="password" type="password" placeholder={t("auth.min4")} minLength={4} required />
              <label>{t("auth.confirmPass")}</label>
              <input name="password2" type="password" placeholder={t("auth.repeatPass")} required />
              <label>{t("auth.securityQ")}</label>
              <input name="security_q" placeholder={t("auth.securityQPh")} required />
              <label>{t("auth.securityA")}</label>
              <input name="security_a" placeholder={t("auth.securityAPh")} required />
              {error && <p className="err">❌ {error}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : t("auth.createAccount")}</button>
              <div className="switch">
                <span>{t("auth.haveAccount")}{" "}
                  <button type="button" className="link" onClick={() => { reset(); setMode("login"); }}>{t("auth.login")}</button>
                </span>
              </div>
            </form>
          )}

          {mode === "forgot" && (
            <form onSubmit={handleForgot} className="auth-form">
              <h2>{t("auth.recoverPass")}</h2>
              <p className="sub">{t("auth.recoverSubtitle")}</p>
              <label>{t("auth.user")}</label>
              <input name="username" placeholder={t("auth.yourUsername")} onBlur={(e) => loadQuestion(e.target.value)} required />
              {securityQ && <p className="hint">{t("auth.question")} {securityQ}</p>}
              <label>{t("auth.answer")}</label>
              <input name="answer" placeholder={t("auth.yourAnswer")} required />
              <label>{t("auth.newPassword")}</label>
              <input name="new_password" type="password" placeholder={t("auth.newPassword")} minLength={4} required />
              {error && <p className="err">❌ {error}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : t("auth.resetPass")}</button>
              <div className="switch">
                <button type="button" className="link" onClick={() => { reset(); setMode("login"); }}>{t("auth.backToLogin")}</button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
