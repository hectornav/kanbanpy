import { useState } from "react";
import { api, auth } from "./api.js";

const FEATURES = [
  "Tablero Kanban multiusuario",
  "Prioridades, etiquetas y fechas",
  "Comparte tareas con tu familia",
  "Sincronización en vivo en cada pantalla"
];

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // login | register | forgot
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);
  const [securityQ, setSecurityQ] = useState("");

  function reset() {
    setError("");
    setOk("");
  }

  async function handleLogin(e) {
    e.preventDefault();
    reset();
    setBusy(true);
    const f = new FormData(e.target);
    try {
      const res = await api.login({
        username: f.get("username").trim(),
        password: f.get("password")
      });
      auth.token = res.access_token;
      onAuthenticated(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    reset();
    const f = new FormData(e.target);
    if (f.get("password") !== f.get("password2")) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setBusy(true);
    try {
      await api.register({
        username: f.get("username").trim(),
        password: f.get("password"),
        security_q: f.get("security_q").trim(),
        security_a: f.get("security_a").trim()
      });
      // Auto-login right after registering.
      const res = await api.login({
        username: f.get("username").trim(),
        password: f.get("password")
      });
      auth.token = res.access_token;
      onAuthenticated(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadQuestion(username) {
    if (!username.trim()) return;
    try {
      const { security_q } = await api.securityQuestion(username.trim());
      setSecurityQ(security_q || "(usuario no encontrado o sin pregunta registrada)");
    } catch {
      setSecurityQ("");
    }
  }

  async function handleForgot(e) {
    e.preventDefault();
    reset();
    setBusy(true);
    const f = new FormData(e.target);
    try {
      await api.resetPassword({
        username: f.get("username").trim(),
        answer: f.get("answer").trim(),
        new_password: f.get("new_password")
      });
      setOk("Contraseña restablecida. Ya puedes iniciar sesión.");
      setMode("login");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <aside className="auth-brand">
        <span className="logo-mark">📋</span>
        <h1>Kanbanpy Pro</h1>
        <p className="brand-tag">Tu forma de trabajar, organizada.</p>
        <ul className="brand-features">
          {FEATURES.map((f) => (
            <li key={f}>✦ {f}</li>
          ))}
        </ul>
      </aside>

      <main className="auth-card">
        <div className="auth-inner">
          {mode === "login" && (
            <form onSubmit={handleLogin} className="auth-form">
              <h2>Bienvenido/a</h2>
              <p className="sub">Inicia sesión para continuar</p>
              <label>Usuario</label>
              <input name="username" autoComplete="username" placeholder="Nombre de usuario" required />
              <label>Contraseña</label>
              <input name="password" type="password" autoComplete="current-password" placeholder="Contraseña" required />
              {error && <p className="err">❌ {error}</p>}
              {ok && <p className="ok">✅ {ok}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : "Iniciar sesión"}</button>
              <div className="switch">
                <button type="button" className="link" onClick={() => { reset(); setMode("forgot"); }}>
                  ¿Olvidaste tu contraseña?
                </button>
                <span>
                  ¿No tienes cuenta?{" "}
                  <button type="button" className="link" onClick={() => { reset(); setMode("register"); }}>
                    Regístrate
                  </button>
                </span>
              </div>
            </form>
          )}

          {mode === "register" && (
            <form onSubmit={handleRegister} className="auth-form">
              <h2>Crear cuenta</h2>
              <p className="sub">Gratis · Sin límites · Sin correo</p>
              <label>Usuario</label>
              <input name="username" placeholder="Elige un nombre" required />
              <label>Contraseña</label>
              <input name="password" type="password" placeholder="Mínimo 4 caracteres" minLength={4} required />
              <label>Confirmar contraseña</label>
              <input name="password2" type="password" placeholder="Repite tu contraseña" required />
              <label>Pregunta de seguridad</label>
              <input name="security_q" placeholder="¿Nombre de tu primera mascota?" required />
              <label>Respuesta (para recuperar cuenta)</label>
              <input name="security_a" placeholder="No distingue mayúsculas" required />
              {error && <p className="err">❌ {error}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : "Crear cuenta"}</button>
              <div className="switch">
                <span>
                  ¿Ya tienes cuenta?{" "}
                  <button type="button" className="link" onClick={() => { reset(); setMode("login"); }}>
                    Inicia sesión
                  </button>
                </span>
              </div>
            </form>
          )}

          {mode === "forgot" && (
            <form onSubmit={handleForgot} className="auth-form">
              <h2>Recuperar contraseña</h2>
              <p className="sub">Responde tu pregunta de seguridad</p>
              <label>Usuario</label>
              <input name="username" placeholder="Tu nombre de usuario" onBlur={(e) => loadQuestion(e.target.value)} required />
              {securityQ && <p className="hint">Pregunta: {securityQ}</p>}
              <label>Respuesta</label>
              <input name="answer" placeholder="Tu respuesta" required />
              <label>Nueva contraseña</label>
              <input name="new_password" type="password" placeholder="Nueva contraseña" minLength={4} required />
              {error && <p className="err">❌ {error}</p>}
              <button className="primary" disabled={busy}>{busy ? "…" : "Restablecer contraseña"}</button>
              <div className="switch">
                <button type="button" className="link" onClick={() => { reset(); setMode("login"); }}>
                  ← Volver al inicio de sesión
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
