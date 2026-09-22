FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
ARG REQUIREMENTS_FILE=requirements.txt
COPY requirements.txt requirements.staging.txt ./
RUN python -m pip install --upgrade pip && pip install -r "$REQUIREMENTS_FILE"
COPY . .
RUN python -m compileall -q .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3)"
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]
