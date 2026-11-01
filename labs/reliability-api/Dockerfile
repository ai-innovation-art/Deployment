# syntax=docker/dockerfile:1
# Pinned Python base image for reproducible builds
ARG PYTHON_IMAGE=python:3.12-slim

# ================= Stage 1: builder (creates virtualenv, dependencies) =================
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy ONLY requirements first — leverage Docker layer caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ================= Stage 2: runtime (minimal attack surface, non-root) =================
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_MODE=normal \
    LOG_LEVEL=info \
    READY_DELAY_SECONDS=0

# Create dedicated non-root user with fixed high UID/GID 10001
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Copy isolated virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code (owned by root, read-only to app user)
COPY app/ ./app/

# Switch to non-root user
USER 10001:10001

EXPOSE 8000

# Docker-level health check (Kubernetes uses probes instead)
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

# Exec form: uvicorn runs as PID 1 to receive SIGTERM directly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
