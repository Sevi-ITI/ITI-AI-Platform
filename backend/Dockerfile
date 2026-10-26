# iti-ai-api: the FastAPI service (step 9.5.2). Build from the repo root:  docker build -t iti-ai-api:dev backend
# Settings and secrets come from the environment when the container starts (compose / docker run), never from here.

# --- Stage 1: install the pinned packages into a virtual environment ---
FROM python:3.11.17-slim-bookworm AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
COPY requirements.txt /tmp/requirements.txt
RUN /venv/bin/pip install -r /tmp/requirements.txt

# --- Stage 2: the image that runs: the venv and the code, nothing else ---
FROM python:3.11.17-slim-bookworm
# libltdl7: mssql-python's SQL Server driver needs it (checked 2026-10-26). tzdata: Manila time in the logs.
# apt over https: the office network blocks plain http to deb.debian.org.
RUN sed -i "s|http://deb.debian.org|https://deb.debian.org|g" /etc/apt/sources.list.d/debian.sources \
 && apt-get update && apt-get install -y --no-install-recommends libltdl7 tzdata \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 iti && mkdir -p /data/uploads && chown iti:iti /data/uploads
COPY --from=build /venv /venv
ENV PATH=/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Manila ITI_UPLOAD_DIR=/data/uploads
WORKDIR /app
COPY --chown=iti:iti . .
USER iti
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
# One process on purpose: the answer queue lives in it (System Guide D12). 0.0.0.0 is inside the container only;
# compose publishes the port on the host's 127.0.0.1.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]