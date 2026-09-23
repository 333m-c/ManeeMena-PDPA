FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies separately so source edits can reuse the cached layer.
COPY requirements.txt requirements-docker.txt ./
RUN python -m pip install --no-cache-dir -r requirements-docker.txt \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin maneemena

COPY app.py samples.py team.py ./
COPY regex/ ./regex/
COPY templates/ ./templates/
COPY static/ ./static/

USER maneemena

EXPOSE 8000

ENV GITHUB_URL=https://github.com/333m-c/ManeeMena-PDPA

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/rules', timeout=3).close()"]

# Gunicorn imports app:app, so the local-only development server is not started.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-tmp-dir", "/dev/shm", "--error-logfile", "-", "app:app"]
