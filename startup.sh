#!/usr/bin/env bash
# startup.sh — SiteDocs pipeline startup for Railway/Docker.
# Runs: export → ingest → dashboard (with retry for Postgres readiness).
set -euo pipefail

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ── 1. SiteDocs export ──────────────────────────────────────────────
log "═══ Step 1: SiteDocs data export ═══"
if python -m src.main; then
    log "Export completed successfully"
else
    export EXIT_CODE=$?
    log "WARNING: Export failed (exit $EXIT_CODE) — will use stub CSVs if available"
fi

# ── 2. Warehouse ingest ─────────────────────────────────────────────
log "═══ Step 2: Warehouse ingest ═══"
if [ -z "${DATABASE_URL:-}" ]; then
    log "WARNING: DATABASE_URL not set — skipping ingest, dashboard will show empty data"
else
    # Retry Postgres connection up to 5 times (handles startup race)
    for i in $(seq 1 5); do
        if python -c "
import sys
from sqlalchemy import create_engine, text
url = '${DATABASE_URL}'
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql://', 1)
if 'psycopg2' not in url and 'psycopg' not in url:
    url = url.replace('postgresql://', 'postgresql+psycopg2://', 1)
try:
    eng = create_engine(url, pool_pre_ping=True)
    with eng.connect() as c:
        c.execute(text('SELECT 1'))
    print('Postgres OK')
except Exception as e:
    print(f'Postgres not ready: {e}')
    sys.exit(1)
"; then
            log "Postgres is accepting connections"
            break
        else
            log "Postgres not ready yet (attempt $i/5) — waiting 5s..."
            sleep 5
        fi
    done

    if python database/ingest.py; then
        log "Ingest completed successfully"
    else
        log "WARNING: Ingest failed — dashboard may show empty data"
    fi
fi

# ── 3. Dashboard ────────────────────────────────────────────────────
log "═══ Step 3: Starting dashboard ═══"
PORT="${PORT:-5001}"
log "Dashboard serving on http://0.0.0.0:$PORT"
exec gunicorn -k uvicorn.workers.UvicornWorker visualize_fasthtml.app:app \
    --bind "0.0.0.0:$PORT" --workers 2 --timeout 120
