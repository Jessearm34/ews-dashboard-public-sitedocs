FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY visualize_fasthtml/requirements.txt ./visualize_fasthtml-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r visualize_fasthtml-requirements.txt

COPY src ./src
COPY config ./config
COPY visualize_fasthtml ./visualize_fasthtml
COPY refresh.py ./refresh.py
COPY database ./database

RUN mkdir -p /app/output

EXPOSE 5001

CMD ["sh", "-c", "\
  echo '═══ Exporting SiteDocs data... ═══' && \
  python -m src.main || echo 'Export failed (API key missing?); skipping...' && \
  echo '═══ Ingesting into warehouse... ═══' && \
  python database/ingest.py || echo 'Ingest failed; skipping...' && \
  echo '═══ Starting dashboard... ═══' && \
  gunicorn -k uvicorn.workers.UvicornWorker visualize_fasthtml.app:app \
    --bind 0.0.0.0:${PORT:-5001} --workers 2 --timeout 120 \
"]
