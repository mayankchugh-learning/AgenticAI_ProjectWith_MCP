# syntax=docker/dockerfile:1
#
# Production image. The React frontend is built once, then served by the FastAPI backend
# on a single port. All configuration comes from environment variables at run time (variable
# names are listed in .env.example). No .env file, key or credential is copied into the image
# (see .dockerignore).

# ---- Stage 1: build the frontend ------------------------------------------------------
FROM node:20.19.5-alpine3.22 AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---- Stage 2: install Python dependencies into a virtualenv ---------------------------
FROM python:3.12.10-slim-bookworm AS python-builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt


# ---- Stage 3: runtime image (no build tools, non-root) --------------------------------
FROM python:3.12.10-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Unprivileged user; fixed numeric ids make file ownership predictable.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=python-builder /opt/venv /opt/venv
COPY --chown=app:app backend/ ./backend/
COPY --from=frontend-builder --chown=app:app /app/frontend/dist ./frontend/dist

# The logger writes ./logs relative to the working directory, so that folder must be writable.
RUN mkdir -p /app/logs && chown app:app /app/logs

USER app

# Cloud Run and similar platforms set PORT; 8080 is the default.
EXPOSE 8080

# Liveness only: /api/health does not call Google Cloud or Gemini. The start period leaves
# time for the Python imports at startup.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8080'), timeout=3)"]

# `exec` makes uvicorn the main process, so it receives SIGTERM directly and can shut down cleanly.
CMD ["sh", "-c", "exec uvicorn api.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}"]
