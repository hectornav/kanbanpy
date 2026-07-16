# syntax=docker/dockerfile:1
#
# Kanbanpy Pro — hybrid "Option C" image.
# Stage 1 builds the React PWA; stage 2 runs the FastAPI backend and serves
# the built PWA, so one container covers the whole stack on your NAS.

# ── Stage 1: build the PWA ──────────────────────────────────────────────────
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KANBAN_ENV=production \
    KANBAN_DB_PATH=/data/kanban.db

WORKDIR /app/server
COPY server/requirements.txt ./
RUN pip install -r requirements.txt

COPY server/ /app/server/
# Built PWA lands where main.py expects it: /app/web/dist
COPY --from=web /web/dist /app/web/dist

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

# Simple container healthcheck against the API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
