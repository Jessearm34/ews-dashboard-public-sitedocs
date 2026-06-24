# SiteDocs Safety Dashboard (FastHTML)

An interactive, single-page HSE executive dashboard built with
[FastHTML](https://fastht.ml) + HTMX + Plotly, styled to match the
EWS design system.  It reads **only** real SiteDocs safety data from
the PostgreSQL warehouse and never fabricates numbers.

## Pages

- **HSE Overview** — the vital signs: active workers, overdue certs,
  open incidents, equipment readiness, incident trends, JSA status.
- **Incidents** — incident log, severity breakdown, trend by month,
  open investigation status.
- **Workers** — workforce roster, active/inactive split, certification
  coverage, expiring certs.
- **Certifications** — expiry profile, coverage gaps, certs by type.
- **Equipment** — equipment roster, by type/location, status.

## Data sources

| Table | Used for |
| --- | --- |
| `sitedocs_workers` | Workforce counts, active/inactive split |
| `sitedocs_equipment` | Equipment roster, status by location |
| `sitedocs_incidents` | Incident log, trends, severity, status |
| `sitedocs_certifications` | Expiry profile, certification coverage |
| `sitedocs_jsa` | Safe-work permit status |

## Run

```bash
cd /path/to/ews-dashboard-public-sitedocs
pip install -r visualize_fasthtml/requirements.txt
python visualize_fasthtml/app.py
# open http://localhost:5001
```

## Production

```bash
gunicorn visualize_fasthtml.wsgi:app --bind 0.0.0.0:5001 --workers 2
```

Or use the Docker Compose setup (see root README).
