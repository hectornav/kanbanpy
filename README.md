# 📋 Kanbanpy Pro v2.0 — Hybrid (self-hosted)

**Kanbanpy Pro** is a premium task-management Kanban with an Apple-inspired dark
UI. It now runs as a **hybrid, self-hosted stack** (architecture "Option C"):

```
server/   → FastAPI core: REST + WebSocket, JWT + argon2 auth, SQLite (WAL).
            Also serves the built PWA, so one container is the whole app.
web/      → React PWA (Vite): works in any browser, installable on mobile.
kanban_app/ → the original PyQt6 app, now an optional native desktop client
              that talks to the same API.
```

One backend, two clients, all sharing the same data. Lives on your NAS,
reachable from every screen.

---

## 🚀 Run it on your NAS (Docker — recommended)

```bash
# 1. Set your signing key
cp .env.example .env
python3 -c "import secrets; print('KANBAN_SECRET_KEY=' + secrets.token_hex(32))" >> .env

# 2. Build once and start (npm install + PWA build happen inside the image)
docker compose up -d --build

# 3. Open it
#    http://<nas-ip>:8000
```

Your data persists in the `kanban-data` Docker volume across rebuilds.

### 📱 Reach it from your phone, anywhere (Tailscale)

Install [Tailscale](https://tailscale.com) on the NAS host and on your phone,
then open `http://<nas-hostname>.<tailnet>.ts.net:8000`. No open ports, no public
domain, end-to-end encrypted. On the phone, use the browser's **"Add to Home
Screen"** to install the PWA. A Tailscale sidecar option is documented in
`docker-compose.yml`.

---

## 🧑‍💻 Local development

**Backend**
```bash
cd server
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload           # http://localhost:8000
python test_smoke.py                     # end-to-end API smoke test
```

**Web PWA**
```bash
cd web
npm install
npm run dev                              # http://localhost:5173 (proxies /api + /ws)
```

**Desktop client (PyQt6) against the API**
```bash
cd kanban_app
pip install -r ../requirements.txt
KANBAN_API_URL=http://localhost:8000 python main.py
```
Without `KANBAN_API_URL`, the desktop app falls back to its legacy local SQLite
database and runs fully standalone.

---

## 🔐 Security

- Passwords and security answers are hashed with **argon2id** (per-hash salt).
- Auth uses signed **JWT** bearer tokens; `KANBAN_SECRET_KEY` is required in prod.
- Per-task authorization: only owners can edit/delete/share; shared users can
  view and move.
- The desktop client no longer stores your password in plaintext.

---

## 🏗️ How the pieces fit

| Layer | Tech | Role |
|-------|------|------|
| API core | FastAPI + Uvicorn | REST, WebSocket live sync, auth |
| Storage | SQLite (WAL mode) | Single-file DB, ideal for a small/family instance |
| Web client | React + Vite (PWA) | Browser + installable mobile app |
| Desktop client | PyQt6 | Optional native window, same API |
| Deploy | Docker + Tailscale | One container on your NAS, private remote access |

*Kanbanpy Pro v2.0 — hnavarro*
