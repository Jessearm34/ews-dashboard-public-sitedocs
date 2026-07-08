"""EWS SiteDocs Safety Dashboard — FastHTML.

A single-page, HTMX-driven HSE executive dashboard styled after the EWS
design system.  Populated **only** with real SiteDocs data from the
PostgreSQL warehouse (``sitedocs_*`` tables).
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from os import getenv
from pathlib import Path
from urllib.parse import parse_qs, urlencode

# Load .env from project root (app runs from visualize_fasthtml/)
from dotenv import load_dotenv as _load_dotenv
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    _load_dotenv(_env_path)

import pandas as pd
from fasthtml.common import *

try:
    import charts as C
    import data as D
except ImportError:
    from visualize_fasthtml import charts as C
    from visualize_fasthtml import data as D

# --------------------------------------------------------------------------- #
# App + global styles
# --------------------------------------------------------------------------- #

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

STYLE = Style("""
:root {
  --navy: #0a1f33; --navy-2: #0d2840; --page: #eef2f7; --card: #ffffff;
  --ink: #0f172a; --muted: #64748b; --line: #e2e8f0; --accent: #2563eb;
  --good: #16a34a; --bad: #dc2626; --warn: #ea580c;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, system-ui, -apple-system, sans-serif;
       background: var(--page); color: var(--ink); }
.layout { display: flex; min-height: 100vh; }

/* Sidebar */
.sidebar { width: 232px; flex: 0 0 232px; background: var(--navy); color: #e8eef5;
           display: flex; flex-direction: column; padding: 22px 14px; }
.brand { display: flex; align-items: center; gap: 10px; padding: 6px 8px 20px; }
.brand .mark { font-size: 22px; }
.brand .name { font-weight: 800; font-size: 14px; line-height: 1.15; letter-spacing: .04em; }
.brand .name small { display:block; font-weight:600; font-size:10px; color:#7e93a8; letter-spacing:.14em; }
.nav { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
.nav a { display: flex; align-items: center; gap: 11px; padding: 10px 12px; border-radius: 10px;
         color: #b8c6d6; text-decoration: none; font-size: 14px; font-weight: 500; cursor: pointer; }
.nav a:hover { background: var(--navy-2); color: #fff; }
.nav a.active { background: var(--accent); color: #fff; }
.sidebar .foot { margin-top: auto; font-size: 11px; color: #64788f; padding: 8px; }

/* Main */
.main { flex: 1; min-width: 0; padding: 22px 26px 40px; }
.header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
.header h1 { margin: 0; font-size: 26px; font-weight: 800; }
.header .crumbs { color: var(--muted); font-size: 13px; margin-top: 4px; }
.header .refreshed { text-align: right; color: var(--muted); font-size: 12px; }
.header .refreshed .pill { display:inline-block; background:#fff; border:1px solid var(--line);
        border-radius: 20px; padding: 6px 12px; font-weight:600; color:var(--ink); }

/* KPI cards */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(176px, 1fr)); gap: 14px; margin-bottom: 20px; }
.kpi { background: var(--card); border:1px solid var(--line); border-radius: 16px; padding: 16px 18px;
       text-decoration: none; color: inherit; transition: box-shadow .15s, transform .15s, border-color .15s; }
.kpi:hover { box-shadow: 0 12px 26px rgba(15,23,42,.10); transform: translateY(-2px); }
.kpi .k-label { color: var(--muted); font-size: 13px; font-weight: 600; }
.kpi .k-value { font-size: 28px; font-weight: 800; margin: 6px 0 4px; }
.kpi .k-delta { font-size: 12.5px; font-weight: 600; }
.kpi .k-hint { color:#94a3b8; font-size: 11px; margin-top:6px; }
.kpi .k-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px;
                border-radius: 999px; margin-left: 6px; }
.kpi .k-badge.warn { background:#fef3c7; color:#92400e; }
.kpi .k-badge.danger { background:#fee2e2; color:#b91c1c; }

/* Panels */
.grid { display: grid; gap: 16px; }
.grid.two { grid-template-columns: 2fr 1fr; }
.grid.even { grid-template-columns: 1fr 1fr; }
.grid.three { grid-template-columns: 1fr 1fr 1fr; }
.panel { background: var(--card); border:1px solid var(--line); border-radius: 16px; padding: 16px 18px; min-width: 0; }
.panel h3 { margin: 0 0 12px; font-size: 14px; font-weight: 700; display:flex; align-items:center; gap:8px; }
.panel h3 .dot { width:9px; height:9px; border-radius: 3px; display:inline-block; }
.panel-scroll { max-height: 340px; overflow-y: auto; }
.chart-empty { display:flex; align-items:center; justify-content:center; height: 280px; color: var(--muted);
               border: 1px dashed var(--line); border-radius: 12px; font-size: 13px; }
.mt { margin-top: 16px; }

/* Tables */
.tbl-wrap { overflow-x: auto; }
table.data { width: 100%; border-collapse: collapse; font-size: 13px; }
table.data th { text-align: left; color: var(--muted); font-weight: 600; padding: 8px 10px;
                border-bottom: 2px solid var(--line); white-space: nowrap; }
table.data td { padding: 8px 10px; border-bottom: 1px solid #f1f5f9; white-space: nowrap; }
table.data td.num, table.data th.num { text-align: right; }
.badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background:#e2e8f0; color:#475569; }
.badge.green { background:#dcfce7; color:#15803d; }
.badge.red { background:#fee2e2; color:#b91c1c; }
.badge.warn { background:#fef3c7; color:#92400e; }
.note { color: var(--muted); font-size: 12px; }
.htmx-indicator { opacity: 0; transition: opacity .2s; font-size: 12px; color: var(--accent); }
.htmx-request .htmx-indicator { opacity: 1; }
""")

app, rt = fast_app(
    pico=False,
    hdrs=(
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="stylesheet",
             href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"),
        Script(src=PLOTLY_CDN),
        STYLE,
    ),
    secret_key=getenv("FASTHTML_SECRET_KEY", "please-change-this-secret"),
)

# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #

SECTIONS = [
    ("hse", "HSE Overview", "🛡️"),
    ("forms", "Forms & JSAs", "📋"),
    ("compliance", "Compliance", "✅"),
    ("incidents", "Incidents", "⚠️"),
    ("workers", "Workers", "👷"),
    ("certifications", "Certifications", "🎓"),
    ("equipment", "Equipment", "🔧"),
    ("locations", "Locations", "📍"),
    ("signatures", "Signatures", "✍️"),
    ("reports", "Reports & Trends", "📊"),
]

# Sections that have actual data (hide empty ones)
SECTION_DATA_GATE = {
    "incidents": lambda ds: len(ds.incidents) > 0,
    "certifications": lambda ds: len(ds.certifications) > 0,
    "equipment": lambda ds: len(ds.equipment) > 0,
}


def visible_sections(ds: D.Dataset) -> list:
    """Return only sections that have data (or no data gate)."""
    out = []
    for key, label, icon in SECTIONS:
        gate = SECTION_DATA_GATE.get(key)
        if gate and not gate(ds):
            continue
        out.append((key, label, icon))
    return out

SWAP = dict(hx_target="#app", hx_swap="outerHTML", hx_indicator="#loading")

KPI_SETS = {
    "hse": ["active_workers", "total_forms", "total_signatures", "total_locations", "form_types", "total_schedules"],
    "forms": ["total_forms", "form_types", "form_templates", "total_signatures"],
    "compliance": ["total_schedules", "total_signatures", "active_workers", "expiring_certs"],
    "incidents": ["total_incidents", "open_incidents", "investigation", "ytd_incidents"],
    "workers": ["active_workers", "total_workers", "contractors", "trained_workers"],
    "certifications": ["total_certs", "expired_certs", "expiring_certs", "trained_workers"],
    "equipment": ["equipment_active", "equipment_total"],
    "locations": ["total_locations", "active_workers", "total_forms"],
    "signatures": ["total_signatures", "active_workers", "total_schedules"],
    "reports": ["total_forms", "total_signatures", "active_workers", "total_schedules"],
}

# --------------------------------------------------------------------------- #
# State & auth
# --------------------------------------------------------------------------- #


def get_state(req) -> dict:
    q = req.query_params
    return {
        "section": q.get("section", "hse"),
    }


AUTH_LOGIN_DOMAIN = getenv("DASHBOARD_LOGIN_DOMAIN", "energywatersolutions.com").strip().lower()
AUTH_PASSWORD = getenv("DASHBOARD_LOGIN_PASSWORD")
AUTH_PASSWORD_HASH = getenv("DASHBOARD_LOGIN_PASSWORD_HASH", "").strip()


def _password_hash(password: str) -> str:
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), b"fasthtml-dashboard", 120_000)
    return digest.hex()


def verify_password(password: str) -> bool:
    if not AUTH_PASSWORD and not AUTH_PASSWORD_HASH:
        return False
    if AUTH_PASSWORD_HASH:
        return compare_digest(_password_hash(password), AUTH_PASSWORD_HASH)
    return compare_digest(password, AUTH_PASSWORD or "")


def email_allowed(email: str) -> bool:
    if not email:
        return False
    return email.strip().lower().endswith(f"@{AUTH_LOGIN_DOMAIN}")


def user_is_authenticated(req) -> bool:
    try:
        return bool(req.session.get("user"))
    except AssertionError:
        return False


def require_login(req):
    if user_is_authenticated(req):
        return None
    next_url = str(req.url.path)
    if req.url.query:
        next_url += f"?{req.url.query}"
    return Redirect(f"/login?{urlencode({'next': next_url})}")


def parse_form(body: bytes) -> dict[str, str]:
    raw = parse_qs(body.decode("utf-8", errors="ignore"))
    return {k: v[0] for k, v in raw.items() if v}


def _clean_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def url(state: dict, **over) -> str:
    return "/view?" + urlencode({**state, **over})


# --------------------------------------------------------------------------- #
# Fragment builders
# --------------------------------------------------------------------------- #


def _fmt(v, unit="") -> str:
    if isinstance(v, (int, float)):
        if unit == "$":
            return f"${abs(v)/1e6:,.2f}M" if abs(v) >= 1e6 else f"${abs(v)/1e3:,.1f}K" if abs(v) >= 1e3 else f"${v:,.0f}"
        if float(v).is_integer():
            return f"{int(v):,}"
        return f"{v:,.1f}"
    return str(v)


def kpi_card(label, value, hint="", badge=None, badge_class="", rag=None):
    inner = [Div(label, cls="k-label"), Div(_fmt(value), cls="k-value")]
    if rag:
        rag_color = D.rag_color(rag) if hasattr(D, 'rag_color') else {"green":"#16a34a","amber":"#ea580c","red":"#dc2626"}.get(rag, "#64748b")
        inner.append(Div(Span("●", style=f"color:{rag_color}; margin-right: 4px;"),
                         Span(D.rag_badge(rag) if hasattr(D, 'rag_badge') else rag, style=f"color:{rag_color}; font-size:11px; font-weight:600")))
    if badge:
        inner.append(Div(Span(badge, cls=f"k-badge {badge_class}")))
    if hint:
        inner.append(Div(hint, cls="k-hint"))
    return Div(*inner, cls="kpi")


def kpi_row(state: dict, ds: D.Dataset):
    """Build the KPI strip for the current section."""
    cards = []

    wc = D.worker_counts(ds.workers)
    sc = D.schedule_counts(ds.schedules)
    fc = D.form_counts(ds.forms)
    lc = D.location_counts(ds.locations)
    wp = D.worker_participation(ds.workers, ds.forms)

    def _card(label, value, hint="", badge=None, bc="", rag=None):
        return kpi_card(label, value, hint, badge, bc, rag)

    sec = state["section"]

    # ── HSE Overview: Hero KPIs ──
    if sec == "hse":
        sched_rag = D.rag_status(sc["completion_pct"], 80, 60, good_when_high=True)
        overdue_rag = D.rag_status(sc["overdue"], 5, 15, good_when_high=False)
        part_rag = D.rag_status(wp["pct"], 80, 60, good_when_high=True)
        brc = D.bbso_rir_counts(ds.forms)
        cards = [
            _card("Schedule Compliance", f"{sc['completion_pct']:.0f}%",
                  f"{sc['completed']}/{sc['total']} completed",
                  rag=sched_rag),
            _card("Overdue Items", sc["overdue"],
                  f"+ {sc['late']} late · {sc['cancelled']} cancelled",
                  badge="●" if sc["overdue"] > 0 else "", bc="red" if sc["overdue"] > 0 else "",
                  rag=overdue_rag),
            _card("BBSO", brc["total_bbso"],
                  f"{brc['bbso_this_month']} this month · {brc['bbso_contributors']} contributors",
                  badge="BBSO", bc="green"),
            _card("RIR / Near Miss", brc["total_rir"],
                  f"{brc['rir_this_month']} this month · {brc['rir_contributors']} contributors",
                  badge="RIR", bc="green"),
            _card("Worker Participation", f"{wp['pct']:.0f}%",
                  f"{wp['participating']}/{wp['active_workers']} active workers",
                  rag=part_rag),
        ]

    # ── Forms ──
    elif sec == "forms":
        cards = [
            _card("Total Forms", fc["total"], "All submitted forms"),
            _card("This Month", fc.get("month", 0), "Current period"),
            _card("Active Workers", wc["active"], f"of {wc['total']} total"),
        ]

    # ── Compliance ──
    elif sec == "compliance":
        sched_rag = D.rag_status(sc["completion_pct"], 80, 60)
        overdue_rag = D.rag_status(sc["overdue"], 5, 15, good_when_high=False)
        cards = [
            _card("Completion Rate", f"{sc['completion_pct']:.0f}%",
                  f"{sc['completed']}/{sc['total']} items", rag=sched_rag),
            _card("Overdue", sc["overdue"], "Needs immediate attention",
                  badge="●" if sc["overdue"] else "", bc="red" if sc["overdue"] else "",
                  rag=overdue_rag),
            _card("Late", sc["late"], "Past scheduled date"),
            _card("Cancelled", sc["cancelled"], "Removed from schedule"),
        ]

    # ── Workers ──
    elif sec == "workers":
        cards = [
            _card("Active Workers", wc["active"], f"of {wc['total']} total"),
            _card("Contractors", wc["contractors"], f"of {wc['total']} workers",
                  badge=f"{wc['employees']} employees", bc="green"),
            _card("Participating (This Month)", f"{wp['pct']:.0f}%",
                  f"{wp['participating']}/{wp['active_workers']} submitted ≥1 form",
                  rag=D.rag_status(wp["pct"], 80, 60)),
        ]

    # ── Remaining sections (minimal, data-driven) ──
    elif sec == "incidents":
        inc_c = D.incident_counts(ds.incidents)
        cards = [
            _card("Total Incidents", inc_c["total"], "All time"),
            _card("Open", inc_c["open"], "Needs action",
                  badge="!" if inc_c["open"] else "", bc="red" if inc_c["open"] else ""),
        ]

    elif sec == "certifications":
        cert_s = D.cert_summary(ds.certifications, ds.workers)
        expired = cert_s["expired"]
        cards = [
            _card("Total Certs", cert_s["total"], "All certifications"),
            _card("Active", cert_s["active"], "Current",
                  badge="✓" if cert_s["active"] else "", bc="green" if cert_s["active"] else ""),
            _card("Expired", expired, "Needs renewal",
                  badge="!" if expired else "", bc="red" if expired else ""),
        ]

    elif sec == "equipment":
        eq_c = D.equipment_counts(ds.equipment)
        cards = [
            _card("Total Equipment", eq_c["total"], "All registered"),
            _card("Active", eq_c["active"], "In service",
                  badge="✓" if eq_c["active"] else "", bc="green" if eq_c["active"] else ""),
        ]

    elif sec == "locations":
        cards = [
            _card("Locations", lc["total"], "Active sites"),
            _card("Forms Submitted", fc["total"], f"Across {lc['total']} locations"),
        ]

    elif sec == "signatures":
        sig_c = D.signature_counts(ds.signatures)
        cards = [
            _card("Signatures", sig_c["total"], "All records"),
            _card("Schedule Items", sc["total"], "Scheduled"),
        ]

    elif sec == "reports":
        cards = [
            _card("Forms", fc["total"], "All submitted"),
            _card("Schedules", sc["total"], f"{sc['completed']} completed"),
            _card("Signatures", D.signature_counts(ds.signatures)["total"], "All time"),
            _card("Locations", lc["total"], "Active"),
        ]

    return Div(*cards, cls="kpis")


def panel(title: str, body, dot_color: str = "#2563eb", scroll: bool = False):
    cls = "panel panel-scroll" if scroll else "panel"
    return Div(
        H3(Span(cls="dot", style=f"background:{dot_color}"), title),
        NotStr(body) if isinstance(body, str) else body,
        cls=cls,
    )


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


def incident_table(incidents: pd.DataFrame):
    if incidents.empty:
        return NotStr(C.empty("No incidents"))
    df = incidents.sort_values("CreatedOn", ascending=False).head(50)
    rows = []
    for _, r in df.iterrows():
        created = str(r.get("CreatedOn", ""))[:10] if pd.notna(r.get("CreatedOn")) else ""
        name = r.get("Name", "—")[:80]
        tname = r.get("TypeName", "—")
        status = r.get("LatestStatus", "")
        st_cls = "badge red" if status.lower() in ("open",) else ("badge warn" if status.lower() in ("investigation",) else "badge green")
        rows.append(Tr(
            Td(created),
            Td(tname),
            Td(name),
            Td(Span(status, cls=st_cls)),
        ))
    head = Tr(Th("Date"), Th("Type"), Th("Description"), Th("Status"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def worker_table(workers: pd.DataFrame):
    if workers.empty:
        return NotStr(C.empty("No worker data"))
    df = D.worker_roster(workers).head(100)
    rows = []
    for _, r in df.iterrows():
        rows.append(Tr(
            Td(r["_Name"]),
            Td(r.get("Email", "—")),
            Td(r["_Type"]),
            Td(r["_Company"]),
            Td(Span(r["_ActiveLabel"], cls="badge green" if r["Active"] else "badge")),
            Td(str(r.get("DateHired", ""))[:10] if pd.notna(r.get("DateHired")) else "—"),
        ))
    head = Tr(Th("Name"), Th("Email"), Th("Type"), Th("Company"), Th("Status"), Th("Hired"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def cert_table(certs: pd.DataFrame, workers: pd.DataFrame):
    if certs.empty:
        return NotStr(C.empty("No certification data"))
    df = D.cert_records(certs, workers)
    df = df.head(100)
    rows = []
    for _, r in df.iterrows():
        expires = r.get("Expires", pd.NaT)
        if pd.notna(expires):
            days_left = (expires - pd.Timestamp(datetime.now().date())).days
            if days_left < 0:
                cls_ = "badge red"
                lbl = f"Expired ({abs(days_left)}d)"
            elif days_left <= 90:
                cls_ = "badge warn"
                lbl = f"{days_left}d left"
            else:
                cls_ = "badge green"
                lbl = str(expires.date())
        else:
            cls_ = "badge"
            lbl = "No expiry"
        rows.append(Tr(
            Td(r.get("_WorkerName", "—")),
            Td(r.get("CertificationTypeName", "—")),
            Td(Span(lbl, cls=cls_)),
            Td(str(r.get("Acquired", ""))[:10] if pd.notna(r.get("Acquired")) else "—"),
        ))
    head = Tr(Th("Worker"), Th("Certification"), Th("Expiry"), Th("Acquired"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def equipment_table(equipment: pd.DataFrame):
    if equipment.empty:
        return NotStr(C.empty("No equipment data"))
    df = equipment.sort_values("Name")
    rows = []
    for _, r in df.iterrows():
        deleted = _clean_bool(r.get("IsDeleted", False))
        rows.append(Tr(
            Td(r.get("Name", "—")),
            Td(r.get("EquipmentTypeName", "—")),
            Td(str(r.get("CreatedOn", ""))[:10] if pd.notna(r.get("CreatedOn")) else "—"),
            Td(Span("Active" if not deleted else "Inactive", cls="badge green" if not deleted else "badge")),
        ))
    head = Tr(Th("Name"), Th("Type"), Th("Created"), Th("Status"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def forms_table(forms: pd.DataFrame):
    if forms.empty:
        return NotStr(C.empty("No forms submitted"))
    df = forms.sort_values("CreatedOn", ascending=False).head(12)
    rows = []
    for _, r in df.iterrows():
        rows.append(Tr(
            Td(r.get("Label", "—")[:60]),
            Td(r.get("DocumentTemplateName", r.get("_FormTypeName", "—"))),
            Td(str(r.get("CreatedOn", ""))[:10] if pd.notna(r.get("CreatedOn")) else "—"),
            Td(Span("✓" if _clean_bool(r.get("HasGoodData", True)) else "?", cls="badge green" if _clean_bool(r.get("HasGoodData", True)) else "badge warn")),
        ))
    head = Tr(Th("Label"), Th("Form Type"), Th("Created"), Th("Status"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def locations_table(locs: pd.DataFrame):
    if locs.empty:
        return NotStr(C.empty("No locations"))
    rows = []
    for _, r in locs.iterrows():
        rows.append(Tr(
            Td(r.get("Name", "—")),
            Td(str(r.get("Id", ""))[:12] + "…"),
        ))
    head = Tr(Th("Name"), Th("ID"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def signatures_table(sigs: pd.DataFrame):
    if sigs.empty:
        return NotStr(C.empty("No signatures"))
    df = sigs.sort_values("CreatedOn", ascending=False).head(100)
    rows = []
    for _, r in df.iterrows():
        name = f"{r.get('SignatoryFirstName', '')} {r.get('SignatoryLastName', '')}".strip()
        if not name:
            name = "—"
        rows.append(Tr(
            Td(name),
            Td(r.get("SignatoryTitle", "—")),
            Td(str(r.get("CreatedOn", ""))[:10] if pd.notna(r.get("CreatedOn")) else "—"),
            Td(r.get("ApprovalStatus", "—")),
        ))
    head = Tr(Th("Signatory"), Th("Title"), Th("Signed"), Th("Status"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


def formtypes_table(ft: pd.DataFrame):
    if ft.empty:
        return NotStr(C.empty("No form types"))
    df = ft.sort_values("Name")
    rows = []
    for _, r in df.iterrows():
        rows.append(Tr(
            Td(r.get("Name", "—")),
        ))
    head = Tr(Th("Form Type Name"))
    return Div(Table(Thead(head), Tbody(*rows), cls="data"), cls="tbl-wrap")


# --------------------------------------------------------------------------- #
# Section bodies
# --------------------------------------------------------------------------- #


def section_body(state: dict, ds: D.Dataset):
    sec = state["section"]

    if sec == "hse":
        return Div(
            Div(panel("Schedule compliance", C.schedule_compliance(ds.schedules), "#dc2626"),
                panel("Forms by category", C.form_category_chart(ds.forms), "#2563eb"),
                cls="grid two"),
            Div(panel("Monthly BBSO", C.bbso_trend(ds.forms), "#7c3aed"),
                panel("Monthly RIR / Near Miss", C.rir_trend(ds.forms), "#ea580c"),
                cls="grid two mt"),
            Div(panel("BBSO & RIR by worker", NotStr(C.bbso_rir_leaderboard_table(ds.workers, ds.forms)),
                "#7c3aed", scroll=True),
                panel("Overdue & late items", NotStr(C.overdue_items_list(ds.schedules)),
                "#dc2626", scroll=True),
                cls="grid mt"),
        )

    if sec == "workers":
        return Div(
            Div(panel("Active vs inactive", C.worker_status(ds.workers), "#2563eb"),
                panel("Employee vs contractor", C.worker_type_split(ds.workers), "#7c3aed"),
                cls="grid even"),
            Div(panel("Worker activity leaderboard", C.worker_leaderboard_table(
                ds.workers, ds.forms, ds.signatures, ds.schedules), "#0e7490", scroll=True), cls="grid mt"),
            Div(panel("Workforce roster", worker_table(ds.workers), "#2563eb", scroll=True), cls="grid mt"),
        )

    if sec == "forms":
        return Div(
            Div(panel("Forms by category", C.form_category_chart(ds.forms), "#2563eb"),
                panel("Monthly trend", C.forms_trend(ds.forms), "#0e7490"),
                cls="grid two"),
            Div(panel("Forms by type", C.form_types_chart(ds.formtypes, ds.forms), "#2563eb"),
                panel("Recent submissions", forms_table(ds.forms), "#2563eb", scroll=True),
                cls="grid two mt"),
        )

    if sec == "compliance":
        return Div(
            Div(panel("Schedule compliance", C.schedule_compliance(ds.schedules), "#dc2626"),
                panel("Forms trend", C.forms_trend(ds.forms), "#2563eb"),
                cls="grid two"),
            Div(panel("Overdue & late items", NotStr(C.overdue_items_list(ds.schedules)),
                "#dc2626", scroll=True), cls="grid mt"),
        )

    if sec == "incidents":
        return Div(
            Div(panel("Incident trend", C.incident_trend(ds.incidents), "#dc2626"),
                panel("By type", C.incident_by_type(ds.incidents), "#0e7490"),
                cls="grid two"),
            Div(panel("Status breakdown", C.incident_status_pie(ds.incidents), "#7c3aed"),
                panel("Incident log", incident_table(ds.incidents), "#dc2626"),
                cls="grid two mt"),
        )

    if sec == "certifications":
        return Div(
            Div(panel("Expiry profile", C.cert_expiry_profile(ds.certifications), "#ea580c"),
                panel("Coverage", C.cert_coverage(ds.certifications, ds.workers), "#16a34a"),
                cls="grid even"),
            Div(panel("Certification records", cert_table(ds.certifications, ds.workers), "#ea580c"),
                cls="grid mt"),
        )

    if sec == "equipment":
        return Div(
            Div(panel("By type", C.equipment_by_type(ds.equipment), "#0e7490"),
                panel("Status", C.equipment_status(ds.equipment), "#0e7490"),
                cls="grid even"),
            Div(panel("Roster", equipment_table(ds.equipment), "#0e7490"), cls="grid mt"),
        )

    if sec == "locations":
        return Div(
            Div(panel("Forms trend", C.forms_trend(ds.forms), "#2563eb"),
                panel("All locations", locations_table(ds.locations), "#0e7490", scroll=True),
                cls="grid two"),
        )

    if sec == "signatures":
        return Div(
            Div(panel("Recent signatures", signatures_table(ds.signatures), "#7c3aed"),
                panel("Schedule compliance", C.schedule_compliance(ds.schedules), "#16a34a"),
                cls="grid two"),
        )

    if sec == "reports":
        return Div(
            Div(panel("Forms trend", C.forms_trend(ds.forms), "#2563eb"),
                panel("Schedule compliance", C.schedule_compliance(ds.schedules), "#dc2626"),
                cls="grid two"),
            Div(panel("Recent forms", forms_table(ds.forms), "#2563eb", scroll=True),
                panel("Recent signatures", signatures_table(ds.signatures), "#7c3aed", scroll=True),
                cls="grid two mt"),
        )

    return Div()


# --------------------------------------------------------------------------- #
# Shell
# --------------------------------------------------------------------------- #


def sidebar(state: dict, ds: D.Dataset):
    links = []
    for key, label, icon in visible_sections(ds):
        active = "active" if state["section"] == key else ""
        links.append(A(Span(icon), Span(label), cls=active, hx_get=url(state, section=key), **SWAP))
    return Div(
        Div(Span("🛡️", cls="mark"),
            Span(NotStr("EWS<small>SAFETY DASHBOARD</small>"), cls="name"),
            cls="brand"),
        Div(*links, cls="nav"),
        Div(A("Logout", href="/logout", style="color: #64788f; text-decoration: none; font-size: 11px;"),
            cls="foot"),
        cls="sidebar",
    )


def header(ds: D.Dataset):
    if ZoneInfo:
        now_dt = datetime.now(ZoneInfo("America/Chicago"))
    else:
        now_dt = datetime.now(timezone.utc) - timedelta(hours=5)
    now_str = now_dt.strftime("%b %d, %Y %I:%M %p")
    return Div(
        H1("EWS Safety Dashboard"),
        Div(Span(f"Last refreshed {now_str} (Houston Time)", cls="note"),
            cls="refreshed"),
        cls="header",
    )


def app_shell(state: dict):
    ds = D.load_dataset()
    # Redirect to HSE if the requested section has no data
    visible = {k for k, _, _ in visible_sections(ds)}
    if state["section"] not in visible:
        state["section"] = "hse"
    main = Div(
        header(ds),
        kpi_row(state, ds),
        section_body(state, ds),
        cls="main",
    )
    return Div(sidebar(state, ds), main, id="app", cls="layout")


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@rt("/")
def index(req):
    guard = require_login(req)
    if guard is not None:
        return guard
    return Title("EWS Safety Dashboard"), app_shell(get_state(req))


@rt("/view")
def view(req):
    guard = require_login(req)
    if guard is not None:
        return guard
    return app_shell(get_state(req))


def login_page(error: str | None = None, next_url: str = "/"):
    alert = Div(error, cls="note", style="color: #b91c1c; margin-bottom: 14px;") if error else ""
    form = Form(
        Label("Email", html_for="email"),
        Input(type="email", name="email", id="email", required=True,
              style="width:100%; padding:10px; border:1px solid #d1d5db; border-radius:10px; margin-bottom:12px;"),
        Label("Password", html_for="password"),
        Input(type="password", name="password", id="password", required=True,
              style="width:100%; padding:10px; border:1px solid #d1d5db; border-radius:10px; margin-bottom:16px;"),
        Input(type="hidden", name="next", value=next_url),
        Button("Sign in", type="submit", cls="apply", style="width:100%;"),
        action="/login", method="post",
        style="display:flex; flex-direction:column; gap:8px;"
    )
    return Div(
        Div(
            H1("Dashboard sign in", style="margin-top:0;"),
            Div(f"Access is restricted to @{AUTH_LOGIN_DOMAIN} email addresses.",
                cls="note", style="margin-bottom:18px;"),
            alert,
            form,
            cls="panel",
            style="max-width:420px; width:100%; margin:auto;"
        ),
        cls="main",
        style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:0 18px; background: var(--page);"
    )


@rt("/login")
async def login(req):
    if user_is_authenticated(req):
        return Redirect(req.query_params.get("next", "/"))

    error = None
    next_url = req.query_params.get("next", "/")
    if req.method == "POST":
        try:
            payload = parse_form(await req.body())
        except RuntimeError:
            form = await req.form()
            payload = {k: v for k, v in form.items()}
        email = payload.get("email", "").strip()
        password = payload.get("password", "")
        next_url = payload.get("next", next_url) or "/"
        if email_allowed(email) and verify_password(password):
            req.session["user"] = email.lower()
            return Redirect(next_url)
        error = "Invalid email or password."
    return Title("Login"), login_page(error, next_url)


@rt("/logout")
def logout(req):
    try:
        req.session.clear()
    except AssertionError:
        pass
    return Redirect("/login")


if __name__ == "__main__":
    serve(port=5002)
