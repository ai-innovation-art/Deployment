# syntax=docker/dockerfile:1
# One image, two jobs:
#   default CMD            -> the orders API server
#   python -m app.migrate  -> the db-migrate init container
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

FROM python:3.12-slim
ARG APP_VERSION=1.0
ENV PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" APP_VERSION=${APP_VERSION}
RUN groupadd -g 10001 app && useradd -u 10001 -g app -M -s /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app/ ./app/
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
