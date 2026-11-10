# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install redis==5.0.8 \
 && groupadd -g 10001 app && useradd -u 10001 -g app -M -s /usr/sbin/nologin app
WORKDIR /app
COPY notifier.py .
USER 10001:10001
CMD ["python", "notifier.py"]
