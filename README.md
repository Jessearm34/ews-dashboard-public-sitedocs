# EWS SiteDocs Safety Dashboard

A FastHTML + HTMX + Plotly executive HSE dashboard that reads **real SiteDocs safety data** from the PostgreSQL warehouse.

## Data Pipeline (11 datasets)

| Dataset | Rows | Source Endpoint |
|---------|------|----------------|
| Workers | 26 | `GET /api/v1/workers` |
| Equipment | 0 | `GET /api/v1/equipments` |
| Incidents | 0 | `GET /api/v1/incidentfolders` |
| Certifications | 0 | `GET /api/v1/certifications` |
| Forms | 820 | `GET /api/v1/forms` |
| Locations | 15 | `GET /api/v1/locations` |
| Company Types | 3 | `GET /api/v1/companytypes` |
| Cert Types | 30 | `GET /api/v1/certificationtypes` |
| Form Types | 119 | `GET /api/v1/formtypes` |
| Signatures | 1,096 | `GET /api/v1/signatures` |
| Schedules | 1,892 | `GET /api/v1/schedules/form/search` |

Total: ~4,000 rows of real EWS SiteDocs data.

## Deploy on Railway

### Step 1: Set up Railway Postgres
```bash
railway login
railway init
railway add postgres
```

### Step 2: Set environment variables
```bash
railway variables set SITEDOCS_API_KEY=<your_token>
railway variables set DASHBOARD_LOGIN_DOMAIN=energywatersolutions.com
railway variables set DASHBOARD_LOGIN_PASSWORD=<your_password>
railway variables set FASTHTML_SECRET_KEY=<random_long_string>
```

The `DATABASE_URL` is auto-injected by Railway Postgres.

### Step 3: Deploy
```bash
railway up
```

### Step 4: Run the data pipeline (one-time or cron)
```bash
cd /app
python -m src.main    # pulls SiteDocs → CSVs
python database/ingest.py  # loads CSVs → Postgres
```

Set up a cron job or Railway cron to run every 15-60 minutes.

## Local Development

```bash
cd ~/Projects/ews-dashboard-public-sitedocs
cp .env.example .env
# Fill in SITEDOCS_API_KEY and DATABASE_URL

# Export + ingest
source .venv/bin/activate
python -m src.main
python database/ingest.py

# Run dashboard (requires Python 3.10+ or Docker)
# Option A: Docker
docker compose up -d --build

# Option B: Local (Python 3.10+)
pip install -r visualize_fasthtml/requirements.txt
python visualize_fasthtml/app.py
# → http://localhost:5001
```

## Dashboard Pages

| Page | KPIs | Content |
|------|------|---------|
| 🛡️ HSE Overview | Workers, Forms, Signatures, Locations | All 119 form types, worker stats |
| 📋 Forms & JSAs | Forms, Form Types, Signatures | 820 submitted forms with type/label |
| ✅ Compliance | Schedules, Signatures, Certs | 1,892 scheduled items |
| ⚠️ Incidents | Total, Open, Investigation, YTD | (ready for data) |
| 👷 Workers | Active, Total, Contractors, Trained | 26 worker roster + cert coverage |
| 🎓 Certifications | Total, Active, Expired, Expiring | 30 cert types |
| 🔧 Equipment | Active, Total | (ready for data) |
| 📍 Locations | Locations, Workers, Forms | 15 site locations |
| ✍️ Signatures | Signatures, Workers, Schedules | 1,096 signature records |
| 📊 Reports | Forms, Signatures, Workers | Combined activity view |
