# 📋 Kanbanpy Pro

A premium, **self-hosted** Kanban with an Apple-inspired UI. One FastAPI backend
serves a React **PWA** — install it on your phone, run it on your NAS, use it
from every screen.

```
server/   → FastAPI: REST + WebSocket (live sync), JWT + argon2 auth, SQLite (WAL).
            Also serves the built PWA, so one container is the whole app.
web/      → React PWA (Vite): responsive, installable, offline-capable.
```

## ✨ Features

- **Multiple boards**, drag & drop (touch-friendly), archive + activity history
- **Task detail**: subtasks/checklist, comments, assignees, priorities, tags, due dates
- **Views**: board, list, calendar · search + filters
- **Recurring tasks** and **due-date reminders** (Web Push)
- **3 themes** (Nocturne / Frost / Meridian) + customizable board background
- **i18n**: Català · Español · English
- **AI planner**: describe a project, get a structured task breakdown. Works with
  **Claude**, any **OpenAI-compatible API** (OpenAI, Groq, OpenRouter, …), or a
  local **Ollama** model — configured in-app (admin only), keys stay server-side
- **Offline mode**: loads your last board without a connection; queues changes and
  syncs on reconnect

## 🚀 Deploy on your NAS (Docker)

```bash
# 1. Set a signing key
cp .env.example .env
python3 -c "import secrets; print('KANBAN_SECRET_KEY=' + secrets.token_hex(32))" >> .env

# 2. Build + run (npm install + PWA build happen inside the image)
docker compose up -d --build

# 3. Open http://<nas-ip>:8000
```

Data persists in the `kanban-data` Docker volume. `.env` is gitignored — never commit it.

### 📱 Reach it from anywhere (Tailscale)

Install [Tailscale](https://tailscale.com) on the NAS host and your phone, then open
`http://<nas-hostname>.<tailnet>.ts.net:8000` — no open ports, end-to-end encrypted.
On the phone, "Add to Home Screen" to install the PWA.

### 🔔 Optional features

- **Web Push**: `cd server && python gen_vapid.py >> ../.env`, then relaunch.
- **AI planner**: configure it in-app (⚙ in the "Plan with AI" dialog) or via
  `KANBAN_AI_PROVIDER` + provider vars in `.env` (see `.env.example`).

## 🧑‍💻 Local development

```bash
# Backend
cd server && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000
python test_smoke.py                      # end-to-end API smoke test

# Web (hot reload, proxies /api + /ws to :8000)
cd web && npm install && npm run dev      # http://localhost:5173
```

## 🔐 Security

- Passwords & security answers hashed with **argon2id**; **JWT** bearer auth.
- Login **rate limiting** (brute-force lockout).
- Per-board authorization; AI keys are **write-only** and never sent to the browser.
- `KANBAN_SECRET_KEY` required in production.

*Kanbanpy Pro — hnavarro*
