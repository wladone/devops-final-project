from __future__ import annotations

import html
import json
import mimetypes
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import altair as alt
except ImportError:  # pragma: no cover - altair ships with streamlit in this project
    alt = None

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a project dependency
    yaml = None

try:
    import nbformat
except ImportError:  # pragma: no cover - optional; only needed for the notebook viewer
    nbformat = None


ROOT_DIR = Path(__file__).resolve().parents[1]
REPORT_ROOT = Path(os.getenv("DQ_REPORT_ROOT", str(ROOT_DIR / "reports")))
LOCAL_TIMEZONE = "Europe/Bucharest"
MAIN_TF_FILENAME = "main.tf"
HTML_CLOSE_DIV = "</div>"
LOCAL_TLS_CERTIFICATE_ERROR = "local TLS certificate is self-signed"
QUALITY_SCORE_FIELD = "quality_score:Q"
PROBE_METHODS = ("HEAD", "GET")

# Repeated string literals — extracted so a rename happens in one place and so
# SonarQube's "duplicate literal" rule does not flag every callsite.
DOCKER_COMPOSE_FILE = "docker-compose.yml"
VALIDATORS_MODULE_FILE = "validators.py"
HTML_RULE_GROUP_OPEN = '<div class="rule-group">'

SERVICE_ARGOCD = "Argo CD"
SERVICE_CLASSIC_APP = "Classic App"
SERVICE_K8S_APP = "Kubernetes App"

URL_ARGOCD = "https://127.0.0.1:28080"
URL_CLASSIC_DASHBOARD = "http://localhost:18501"
URL_K8S_DASHBOARD = "http://127.0.0.1:28501"

CAPABILITY_GROUPS = [
    (
        "Delivery",
        [
            ("Jenkins pipeline", ROOT_DIR / "Jenkinsfile"),
            ("Docker image build", ROOT_DIR / "Dockerfile"),
            ("Docker Compose stack", ROOT_DIR / DOCKER_COMPOSE_FILE),
            ("Ansible deploy", ROOT_DIR / "ansible" / "playbook.yml"),
        ],
    ),
    (
        "Platform",
        [
            ("Helm chart", ROOT_DIR / "helm" / "data-quality-monitor" / "Chart.yaml"),
            ("Argo CD apps", ROOT_DIR / "argocd" / "app-dev.yaml"),
            ("Terraform bootstrap", ROOT_DIR / "terraform" / "environments" / "dev" / MAIN_TF_FILENAME),
            ("Monitoring pack", ROOT_DIR / "monitoring" / "prometheus" / "alerts" / "data-quality-alerts.yaml"),
        ],
    ),
    (
        "Security",
        [
            ("Trivy scan config", ROOT_DIR / "security" / "trivy.yaml"),
            ("Cluster policy", ROOT_DIR / "security" / "policies" / "kyverno-require-safe-workloads.yaml"),
            ("SonarQube config", ROOT_DIR / "sonar-project.properties"),
            ("Runbook", ROOT_DIR / "docs" / "runbook.md"),
        ],
    ),
]

PLATFORM_LINKS = [
    ("Jenkins Demo E2E", "http://localhost:8080/job/data-quality-monitor-demo-e2e/"),
    ("Jenkins Home", "http://localhost:8080"),
    ("Jenkins Full Job", "http://localhost:8080/job/data-quality-monitor-full/"),
    ("Jenkins Delivery Job", "http://localhost:8080/job/data-quality-monitor-delivery/"),
    ("SonarQube", "http://localhost:9000"),
    (SERVICE_ARGOCD, URL_ARGOCD),
    (
        "Grafana Operations Dashboard",
        "http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations",
    ),
    ("Grafana Home", "http://localhost:3000"),
    ("Prometheus Targets", "http://localhost:9090/targets"),
    ("Prometheus App Query", "http://localhost:9090/query?g0.expr=sum(up)&g0.tab=table&g0.range_input=1h"),
    ("Classic Dashboard", URL_CLASSIC_DASHBOARD),
    ("Kubernetes Dashboard", URL_K8S_DASHBOARD),
]

PLATFORM_SERVICES = [
    {
        "name": "Jenkins",
        "role": "CI orchestrator",
        "url": "http://localhost:8080/login",
        "ok_statuses": [200],
    },
    {
        "name": "SonarQube",
        "role": "Code quality",
        "url": "http://localhost:9000/api/system/status",
        "ok_statuses": [200],
    },
    {
        "name": SERVICE_ARGOCD,
        "role": "GitOps delivery",
        "url": URL_ARGOCD,
        "ok_statuses": [200],
        "allow_local_tls_certificate_error": True,
    },
    {
        "name": "Grafana",
        "role": "Dashboards",
        "url": "http://localhost:3000/login",
        "ok_statuses": [200],
    },
    {
        "name": "Prometheus",
        "role": "Metrics backend",
        "url": "http://localhost:9090/-/ready",
        "ok_statuses": [200],
    },
    {
        "name": SERVICE_CLASSIC_APP,
        "role": "Ansible deploy",
        "url": URL_CLASSIC_DASHBOARD,
        "ok_statuses": [200],
    },
    {
        "name": SERVICE_K8S_APP,
        "role": "GitOps deploy",
        "url": URL_K8S_DASHBOARD,
        "ok_statuses": [200],
    },
]


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #f5f7fb;
            --panel: #ffffff;
            --panel-alt: #eef4ff;
            --text: #10243e;
            --muted: #61758f;
            --line: #d9e4f2;
            --accent: #0f6fff;
            --good: #1f9d63;
            --warn: #f59e0b;
            --bad: #cf3340;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(15, 111, 255, 0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(31, 157, 99, 0.10), transparent 26%),
                linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
            color: var(--text);
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }

        .hero-panel {
            border: 1px solid rgba(15, 111, 255, 0.10);
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(238, 244, 255, 0.92));
            border-radius: 24px;
            padding: 1.5rem 1.6rem;
            box-shadow: 0 18px 50px rgba(16, 36, 62, 0.08);
            margin-bottom: 1rem;
        }

        .hero-kicker {
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 0.75rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }

        .hero-title {
            font-size: 2.2rem;
            line-height: 1.1;
            font-weight: 800;
            color: var(--text);
            margin: 0;
        }

        .hero-copy {
            color: var(--muted);
            max-width: 960px;
            font-size: 1rem;
            margin-top: 0.65rem;
            margin-bottom: 0;
        }

        .signal-card {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(16, 36, 62, 0.08);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            min-height: 124px;
            box-shadow: 0 12px 32px rgba(16, 36, 62, 0.05);
        }

        .signal-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .signal-value {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            color: var(--text);
            margin-top: 0.35rem;
        }

        .signal-foot {
            color: var(--muted);
            font-size: 0.88rem;
            margin-top: 0.35rem;
        }

        .section-card {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(16, 36, 62, 0.08);
            border-radius: 20px;
            padding: 1.05rem 1.1rem;
            box-shadow: 0 10px 26px rgba(16, 36, 62, 0.05);
        }

        .flow-strip {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.6rem;
            margin-top: 0.25rem;
        }

        .flow-node {
            background: linear-gradient(180deg, #ffffff, #f3f8ff);
            border: 1px solid rgba(15, 111, 255, 0.12);
            border-radius: 18px;
            padding: 0.85rem 0.8rem;
            min-height: 110px;
        }

        .flow-step {
            color: var(--accent);
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }

        .flow-name {
            color: var(--text);
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .flow-desc {
            color: var(--muted);
            font-size: 0.86rem;
            line-height: 1.35;
        }

        .capability-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
        }

        .capability-card {
            border-radius: 18px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(16, 36, 62, 0.08);
            box-shadow: 0 10px 24px rgba(16, 36, 62, 0.05);
        }

        .capability-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.7rem;
        }

        .capability-pill {
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-left: 0.35rem;
        }

        .capability-pill.ok {
            background: rgba(31, 157, 99, 0.12);
            color: var(--good);
        }

        .capability-pill.missing {
            background: rgba(207, 51, 64, 0.10);
            color: var(--bad);
        }

        .artifact-tag {
            display: inline-block;
            border-radius: 999px;
            background: rgba(15, 111, 255, 0.10);
            color: var(--accent);
            padding: 0.2rem 0.55rem;
            margin-right: 0.4rem;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.85rem;
            margin-bottom: 1rem;
        }

        .status-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(16, 36, 62, 0.08);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 10px 24px rgba(16, 36, 62, 0.05);
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            word-break: break-word;
        }

        .status-card .status-role:last-child {
            font-size: 0.78rem;
            color: #61758f;
            margin-top: 0.25rem;
        }

        /* Streamlit multiselect chips overflow when many columns are selected;
           let them wrap and shrink a touch so the Issues filter stays usable. */
        div[data-baseweb="select"] [data-baseweb="tag"] {
            margin: 0.15rem 0.2rem 0.15rem 0 !important;
            max-width: 100%;
            white-space: normal !important;
        }
        div[data-baseweb="select"] > div {
            flex-wrap: wrap !important;
        }

        .status-card.ok {
            border-color: rgba(31, 157, 99, 0.24);
        }

        .status-card.down {
            border-color: rgba(207, 51, 64, 0.24);
        }

        .status-name {
            color: var(--text);
            font-size: 0.95rem;
            font-weight: 800;
        }

        .status-role {
            color: var(--muted);
            font-size: 0.8rem;
            margin-top: 0.16rem;
        }

        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.52rem;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-top: 0.55rem;
        }

        .status-pill.ok {
            background: rgba(31, 157, 99, 0.12);
            color: var(--good);
        }

        .status-pill.down {
            background: rgba(207, 51, 64, 0.10);
            color: var(--bad);
        }

        .remediation-card {
            border-left: 5px solid var(--accent);
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.7rem;
            box-shadow: 0 10px 22px rgba(16, 36, 62, 0.05);
        }

        .remediation-card.critical {
            border-left-color: var(--bad);
        }

        .remediation-card.warning {
            border-left-color: var(--warn);
        }

        .remediation-title {
            color: var(--text);
            font-weight: 800;
            margin-bottom: 0.18rem;
        }

        .remediation-meta {
            color: var(--muted);
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }

        .remediation-action {
            color: var(--text);
            font-size: 0.92rem;
            line-height: 1.4;
        }

        /* ============================================================
           Top navigation bar — cross-app links
           ============================================================ */
        .top-nav {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.45rem;
            padding: 0.55rem 0.85rem;
            margin: 0 0 1.1rem 0;
            border-radius: 18px;
            background: linear-gradient(180deg, rgba(255,255,255,0.85), rgba(238,244,255,0.75));
            border: 1px solid rgba(15, 111, 255, 0.14);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            box-shadow: 0 10px 30px rgba(16, 36, 62, 0.06);
        }

        .top-nav-brand {
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: var(--accent);
            margin-right: 0.6rem;
            padding: 0.35rem 0.6rem;
            border-radius: 999px;
            background: rgba(15, 111, 255, 0.10);
        }

        .top-nav a, .top-nav a:visited {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.42rem 0.78rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.65);
            color: var(--text);
            font-size: 0.84rem;
            font-weight: 600;
            text-decoration: none;
            border: 1px solid rgba(16, 36, 62, 0.08);
            transition: transform 120ms ease, box-shadow 120ms ease, background 120ms ease;
        }

        .top-nav a:hover {
            transform: translateY(-1px);
            background: rgba(15, 111, 255, 0.10);
            border-color: rgba(15, 111, 255, 0.30);
            box-shadow: 0 6px 14px rgba(15, 111, 255, 0.10);
        }

        .top-nav a.you-are-here {
            background: linear-gradient(135deg, rgba(15,111,255,0.18), rgba(31,157,99,0.14));
            border-color: rgba(15, 111, 255, 0.35);
            color: var(--accent);
            font-weight: 800;
            cursor: default;
        }

        .top-nav a.cross-app {
            background: linear-gradient(135deg, rgba(31,157,99,0.16), rgba(15,111,255,0.10));
            border-color: rgba(31, 157, 99, 0.35);
            color: var(--good);
            font-weight: 700;
        }

        .top-nav .dot {
            width: 0.45rem;
            height: 0.45rem;
            border-radius: 50%;
            background: var(--accent);
            display: inline-block;
        }

        .top-nav .dot.good { background: var(--good); }

        /* ============================================================
           Card / pill hover polish
           ============================================================ */
        .signal-card, .section-card, .flow-node, .capability-card,
        .status-card, .remediation-card {
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }

        .signal-card:hover, .flow-node:hover, .capability-card:hover,
        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 18px 40px rgba(16, 36, 62, 0.10);
            border-color: rgba(15, 111, 255, 0.22);
        }

        /* Live-pulse on the "Online" status pill */
        .status-pill.ok::before {
            content: "";
            display: inline-block;
            width: 0.45rem;
            height: 0.45rem;
            border-radius: 50%;
            background: var(--good);
            margin-right: 0.36rem;
            vertical-align: middle;
            box-shadow: 0 0 0 0 rgba(31, 157, 99, 0.55);
            animation: dq-pulse 1.8s infinite;
        }

        @keyframes dq-pulse {
            0%   { box-shadow: 0 0 0 0 rgba(31, 157, 99, 0.55); }
            70%  { box-shadow: 0 0 0 8px rgba(31, 157, 99, 0); }
            100% { box-shadow: 0 0 0 0 rgba(31, 157, 99, 0); }
        }

        /* ============================================================
           Streamlit tab restyle
           ============================================================ */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
            background: rgba(255, 255, 255, 0.55);
            padding: 0.35rem;
            border-radius: 14px;
            border: 1px solid rgba(16, 36, 62, 0.06);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 0.45rem 0.95rem;
            font-weight: 700;
            color: var(--muted);
            background: transparent;
            transition: background 120ms ease, color 120ms ease;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(15, 111, 255, 0.06);
            color: var(--text);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(15,111,255,0.14), rgba(31,157,99,0.10));
            color: var(--accent) !important;
        }

        /* ============================================================
           Rules & Pipeline tab
           ============================================================ */
        .rule-pill {
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 800;
            margin: 0.18rem 0.25rem 0.18rem 0;
            letter-spacing: 0.03em;
            background: rgba(15, 111, 255, 0.10);
            color: var(--accent);
        }

        .rule-pill.warn  { background: rgba(245, 158, 11, 0.12); color: var(--warn); }
        .rule-pill.crit  { background: rgba(207, 51, 64, 0.10); color: var(--bad); }
        .rule-pill.good  { background: rgba(31, 157, 99, 0.12); color: var(--good); }

        .rule-group {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(16, 36, 62, 0.08);
            border-radius: 18px;
            padding: 0.95rem 1.05rem;
            margin-bottom: 0.7rem;
            box-shadow: 0 10px 24px rgba(16, 36, 62, 0.05);
        }

        .rule-group-title {
            color: var(--text);
            font-weight: 800;
            font-size: 1rem;
            margin-bottom: 0.4rem;
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }

        .rule-group-sub {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 600;
        }

        .stage-row {
            display: grid;
            grid-template-columns: 3.2rem 1fr;
            gap: 0.7rem;
            padding: 0.55rem 0.4rem;
            border-bottom: 1px solid rgba(16, 36, 62, 0.06);
        }

        .stage-row:last-child { border-bottom: none; }

        .stage-num {
            color: var(--accent);
            font-weight: 800;
            font-variant-numeric: tabular-nums;
        }

        .stage-name {
            color: var(--text);
            font-weight: 700;
        }

        .stage-desc {
            color: var(--muted);
            font-size: 0.85rem;
            margin-top: 0.18rem;
        }

        @media (max-width: 1100px) {
            .flow-strip, .capability-grid, .status-grid {
                grid-template-columns: 1fr 1fr;
            }
        }

        @media (max-width: 760px) {
            .flow-strip, .capability-grid, .status-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 1.7rem;
            }
            .top-nav { padding: 0.45rem 0.55rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


REQUIRED_SUMMARY_FIELDS = ("quality_score", "checks_failed", "checks_passed", "row_count")


def discover_runs() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for summary_path in REPORT_ROOT.glob("**/summary.json"):
        try:
            with summary_path.open("r", encoding="utf-8") as handle:
                summary = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(summary, dict) or not all(field in summary for field in REQUIRED_SUMMARY_FIELDS):
            # A summary that does not carry the metrics the dashboard expects is skipped
            # so the run list stays usable when an upstream job writes a partial file.
            continue

        report_dir = summary_path.parent
        relative_run_id = report_dir.relative_to(REPORT_ROOT).as_posix()
        generated_at = pd.to_datetime(summary.get("generated_at_utc"), utc=True, errors="coerce")

        records.append(
            {
                "run_id": relative_run_id,
                "label": f"{relative_run_id} | {generated_at.tz_convert(LOCAL_TIMEZONE).strftime('%d %b %Y %H:%M') if pd.notna(generated_at) else 'unknown time'}",
                # Paths are stored as strings so the runs frame stays
                # Arrow-serialisable (Streamlit renders dataframes via
                # pyarrow, which cannot infer a column of Path objects).
                # Consumers wrap them in Path(...) at the boundary.
                "summary_path": str(summary_path),
                "report_path": str(report_dir / "quality_report.csv"),
                "generated_at": generated_at,
                "row_count": summary.get("row_count", 0),
                "checks_total": summary.get("checks_total", 0),
                "checks_passed": summary.get("checks_passed", 0),
                "checks_failed": summary.get("checks_failed", 0),
                "quality_score": float(summary.get("quality_score", 0.0)),
            }
        )

    if not records:
        return pd.DataFrame()

    runs = pd.DataFrame(records).sort_values("generated_at", ascending=False, na_position="last")
    return runs.reset_index(drop=True)


def load_summary(summary_path: Path) -> dict[str, object]:
    with summary_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_report(report_path: Path) -> pd.DataFrame:
    if not report_path.exists():
        return pd.DataFrame()
    return pd.read_csv(report_path)


def build_artifact_inventory(report_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for artifact in sorted(report_dir.glob("*")):
        if artifact.is_file():
            rows.append(
                {
                    "artifact": artifact.name,
                    "size_kb": round(artifact.stat().st_size / 1024, 2),
                    "modified_at": pd.Timestamp(artifact.stat().st_mtime, unit="s", tz="UTC").tz_convert(LOCAL_TIMEZONE).strftime("%d %b %Y %H:%M:%S"),
                    "path": str(artifact),
                }
            )
    return pd.DataFrame(rows)


def build_capability_table() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for group_name, checks in CAPABILITY_GROUPS:
        for capability_name, path in checks:
            records.append(
                {
                    "group": group_name,
                    "capability": capability_name,
                    "status": "Configured" if path.exists() else "Missing",
                    "path": str(path),
                }
            )
    return pd.DataFrame(records)


def html_div(class_name: str, content: str) -> str:
    return f'<div class="{class_name}">{content}{HTML_CLOSE_DIV}'


def get_platform_probe_host() -> str:
    configured_host = os.getenv("DQ_PLATFORM_PROBE_HOST")
    if configured_host:
        return configured_host

    if Path("/.dockerenv").exists():
        return "host.docker.internal"

    return "localhost"


def rewrite_local_url_for_probe(url: str, probe_host: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return url

    netloc = probe_host
    if parsed.port:
        netloc = f"{probe_host}:{parsed.port}"

    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def request_status_code_once(url: str, method: str) -> tuple[int | None, str, bool]:
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return int(response.status), "", False
    except urllib.error.HTTPError as error:
        return int(error.code), "", error.code == 405
    except urllib.error.URLError as error:
        message = LOCAL_TLS_CERTIFICATE_ERROR if isinstance(error.reason, ssl.SSLCertVerificationError) else str(error.reason)
        return None, message, False
    except TimeoutError:
        return None, "timeout", False
    except OSError as error:
        return None, str(error), False


def request_status_code(url: str) -> tuple[int | None, str]:
    last_error = ""
    for method in PROBE_METHODS:
        status_code, error, should_retry = request_status_code_once(url, method)
        if not should_retry:
            return status_code, error
        last_error = error or f"HTTP {status_code}"

    return None, last_error or "unreachable"


@st.cache_data(ttl=30, show_spinner=False)
def probe_platform_services(probe_host: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for service in PLATFORM_SERVICES:
        probe_url = rewrite_local_url_for_probe(str(service["url"]), probe_host)
        status_code, error = request_status_code(probe_url)
        ok_statuses = set(int(code) for code in service["ok_statuses"])
        tls_error_allowed = bool(service.get("allow_local_tls_certificate_error", False))
        is_ok = status_code in ok_statuses or (tls_error_allowed and error == LOCAL_TLS_CERTIFICATE_ERROR)
        results.append(
            {
                "name": service["name"],
                "role": service["role"],
                "public_url": service["url"],
                "probe_url": probe_url,
                "status_code": status_code,
                "status": "Online" if is_ok else "Check",
                "error": error,
            }
        )
    return results


def build_remediation_plan(report: pd.DataFrame) -> pd.DataFrame:
    if report.empty or "status" not in report.columns:
        return pd.DataFrame()

    failed = report[report["status"] == "FAIL"].copy()
    if failed.empty:
        return pd.DataFrame()

    failed["failed_rows"] = pd.to_numeric(failed["failed_rows"], errors="coerce").fillna(0).astype(int)
    failed["metric_value"] = pd.to_numeric(failed["metric_value"], errors="coerce").fillna(0)

    action_map = {
        "required_columns_present": "Add the missing source column before the file reaches the quality gate.",
        "non_null": "Fix missing values upstream or reject rows where this business-critical field is empty.",
        "unique_key": "Deduplicate the business key and investigate whether the source system produced repeated records.",
        "positive_numeric": "Correct non-numeric, zero, or negative values before financial totals are trusted.",
        "valid_date": "Normalize the date format and quarantine rows with invalid calendar values.",
        "allowed_values": "Map unsupported values to the allowed domain or update the rule if the business list changed.",
        "null_threshold": "Reduce missing values or agree a new tolerance with the data owner.",
    }
    severity_rank = {"critical": 0, "warning": 1}
    failed["priority"] = failed["severity"].map(severity_rank).fillna(2).astype(int)
    failed["recommended_action"] = failed["check_name"].map(action_map).fillna(
        "Review the failed rule, fix the source data, and rerun the Jenkins pipeline."
    )

    return failed.sort_values(["priority", "failed_rows", "check_name"], ascending=[True, False, True]).reset_index(drop=True)


def load_input_sample(summary: dict[str, object], max_rows: int = 20) -> pd.DataFrame:
    input_value = summary.get("input_file")
    if not input_value:
        return pd.DataFrame()

    input_path = Path(str(input_value))
    if not input_path.is_absolute():
        input_path = ROOT_DIR / input_path

    if not input_path.exists() or input_path.suffix.lower() != ".csv":
        return pd.DataFrame()

    return pd.read_csv(input_path, nrows=max_rows)


def render_signal_card(label: str, value: str, footnote: str) -> None:
    card_html = (
        '<div class="signal-card">'
        + html_div("signal-label", html.escape(label))
        + html_div("signal-value", html.escape(value))
        + html_div("signal-foot", html.escape(footnote))
        + HTML_CLOSE_DIV
    )
    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )


def render_flow_strip() -> None:
    nodes = [
        ("Step 01", "Validate", "Python rules check nulls, duplicates, dates, thresholds, and allowed values."),
        ("Step 02", "Test", "Jenkins runs unit tests and validates the reporting flow before packaging."),
        ("Step 03", "Build", "Docker builds an immutable application image ready for promotion."),
        ("Step 04", "Secure", "Trivy and SonarQube can block weak releases before delivery."),
        ("Step 05", "Promote", "Helm and Argo CD turn the repo into a GitOps deployment source."),
        ("Step 06", "Operate", "Prometheus, Grafana, runbooks, and rollback docs support production ops."),
    ]
    html_parts = ['<div class="section-card"><div class="flow-strip">']
    for step, name, desc in nodes:
        html_parts.append(
            '<div class="flow-node">'
            + html_div("flow-step", html.escape(step))
            + html_div("flow-name", html.escape(name))
            + html_div("flow-desc", html.escape(desc))
            + HTML_CLOSE_DIV
        )
    html_parts.append(HTML_CLOSE_DIV + HTML_CLOSE_DIV)
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_capability_cards(capabilities: pd.DataFrame) -> None:
    html_markup = '<div class="capability-grid">'
    for group_name, group_df in capabilities.groupby("group", sort=False):
        html_markup += '<div class="capability-card">' + html_div("capability-title", html.escape(str(group_name)))
        for row in group_df.itertuples(index=False):
            status_class = "ok" if row.status == "Configured" else "missing"
            html_markup += (
                f'<div style="margin-bottom:0.55rem;"><strong>{html.escape(str(row.capability))}</strong>'
                f'<span class="capability-pill {status_class}">{html.escape(str(row.status))}</span><br>'
                f'<span style="color:#61758f;font-size:0.82rem;">{html.escape(str(row.path))}</span>{HTML_CLOSE_DIV}'
            )
        html_markup += HTML_CLOSE_DIV
    html_markup += HTML_CLOSE_DIV
    st.markdown(html_markup, unsafe_allow_html=True)


def render_platform_links() -> None:
    st.markdown("#### Platform / DevOps Links")
    cols = st.columns(3)
    for index, (label, url) in enumerate(PLATFORM_LINKS):
        with cols[index % 3]:
            st.link_button(label, url, use_container_width=True)


def render_platform_health() -> None:
    probe_host = get_platform_probe_host()
    results = probe_platform_services(probe_host)
    online_count = sum(1 for result in results if result["status"] == "Online")
    st.markdown("#### Live Platform Health")
    st.caption(
        f"Health checks run from the dashboard runtime through `{probe_host}`. "
        "The buttons below still open the browser-facing localhost URLs."
    )

    html_parts = ['<div class="status-grid">']
    for result in results:
        is_ok = result["status"] == "Online"
        status_class = "ok" if is_ok else "down"
        status_text = "Online" if is_ok else "Check"
        detail = f"HTTP {result['status_code']}" if result["status_code"] else html.escape(str(result["error"]))
        html_parts.append(
            f'<div class="status-card {status_class}">'
            + html_div("status-name", html.escape(str(result["name"])))
            + html_div("status-role", html.escape(str(result["role"])))
            + f'<span class="status-pill {status_class}">{status_text}</span>'
            + html_div("status-role", html.escape(detail))
            + HTML_CLOSE_DIV
        )
    html_parts.append(HTML_CLOSE_DIV)
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    st.progress(online_count / max(len(results), 1), text=f"{online_count}/{len(results)} platform checks online")


def render_remediation_plan(remediation: pd.DataFrame) -> None:
    if remediation.empty:
        st.success("No remediation needed for this run.")
        return

    st.markdown("#### Recommended Fix Order")
    for index, row in enumerate(remediation.head(5).itertuples(index=False), start=1):
        severity = str(row.severity).lower()
        card_class = "critical" if severity == "critical" else "warning"
        title = f"{index}. {row.check_name} on {row.column_name}"
        meta = f"Severity: {row.severity} | Failed rows: {row.failed_rows} | Metric: {row.metric_value}"
        st.markdown(
            f'<div class="remediation-card {card_class}">'
            + html_div("remediation-title", html.escape(title))
            + html_div("remediation-meta", html.escape(meta))
            + html_div("remediation-action", html.escape(str(row.recommended_action)))
            + HTML_CLOSE_DIV,
            unsafe_allow_html=True,
        )


def render_artifact_downloads(artifacts: pd.DataFrame) -> None:
    if artifacts.empty:
        return

    st.markdown("#### Download Artifacts")
    cols = st.columns(3)
    for index, row in enumerate(artifacts.itertuples(index=False)):
        artifact_path = Path(str(row.path))
        if not artifact_path.exists():
            continue

        mime_type = mimetypes.guess_type(artifact_path.name)[0] or "application/octet-stream"
        with cols[index % 3]:
            st.download_button(
                label=f"Download {artifact_path.name}",
                data=artifact_path.read_bytes(),
                file_name=artifact_path.name,
                mime=mime_type,
                use_container_width=True,
            )


def render_pass_fail_chart(summary: dict[str, object]) -> None:
    passed = int(summary["checks_passed"])
    failed = int(summary["checks_failed"])
    chart_df = pd.DataFrame(
        {
            "status": ["PASS", "FAIL"],
            "count": [passed, failed],
        }
    )

    if alt is None:
        st.bar_chart(chart_df.set_index("status"))
        return

    colors = alt.Scale(domain=["PASS", "FAIL"], range=["#1f9d63", "#cf3340"])
    chart = (
        alt.Chart(chart_df)
        .mark_arc(innerRadius=72, outerRadius=116)
        .encode(theta="count:Q", color=alt.Color("status:N", scale=colors, legend=None))
    )
    st.altair_chart(chart, use_container_width=True)


def render_failed_rows_chart(report: pd.DataFrame) -> None:
    failed = report[report["status"] == "FAIL"].copy()
    if failed.empty:
        st.success("No failed checks in the selected run.")
        return

    failed["failed_rows"] = pd.to_numeric(failed["failed_rows"], errors="coerce").fillna(0)
    failed["label"] = failed["check_name"] + " | " + failed["column_name"]
    failed = failed.sort_values("failed_rows", ascending=False)

    if alt is None:
        st.bar_chart(failed.set_index("label")["failed_rows"])
        return

    chart = (
        alt.Chart(failed)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X("label:N", sort="-y", title="Check"),
            y=alt.Y("failed_rows:Q", title="Failed rows"),
            color=alt.Color(
                "severity:N",
                scale=alt.Scale(domain=["critical", "warning"], range=["#cf3340", "#f59e0b"]),
                legend=None,
            ),
            tooltip=["check_name", "column_name", "severity", "failed_rows", "message"],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def render_trend_chart(runs: pd.DataFrame) -> None:
    if runs.empty:
        st.info("No run history yet — trigger a pipeline run to populate this trend.")
        return

    trend = runs.copy()
    trend["generated_label"] = trend["generated_at"].dt.tz_convert(LOCAL_TIMEZONE).dt.strftime("%d %b %H:%M")

    if alt is None:
        st.line_chart(trend.set_index("generated_label")["quality_score"])
        return

    chart = (
        alt.Chart(trend)
        .mark_line(point={"filled": True, "size": 80}, color="#0f6fff", strokeWidth=3)
        .encode(
            x=alt.X("generated_label:N", title="Run"),
            y=alt.Y(QUALITY_SCORE_FIELD, title="Quality score"),
            tooltip=["label", "quality_score", "checks_failed", "checks_passed"],
        )
    )
    st.altair_chart(chart, use_container_width=True)


@st.cache_data(ttl=15, show_spinner=False)
def load_quality_ladder_summary() -> pd.DataFrame:
    summary_path = REPORT_ROOT / "quality-ladder" / "quality_ladder_summary.csv"
    if not summary_path.exists():
        return pd.DataFrame()

    ladder = pd.read_csv(summary_path)
    for column in ["quality_score", "checks_failed", "checks_passed", "score_delta", "failed_delta"]:
        if column in ladder.columns:
            ladder[column] = pd.to_numeric(ladder[column], errors="coerce").fillna(0)
    return ladder


def render_quality_ladder_chart(ladder: pd.DataFrame) -> None:
    if ladder.empty:
        st.info(
            "No quality-improvement ladder yet — this panel shows the score climbing as fixes are applied. "
            "Run the full pipeline or `scripts/ci/run_quality_ladder.sh` to populate it."
        )
        return

    display = ladder.copy()
    display["step_label"] = display["step"].str.replace("_", " ", regex=False)

    if alt is None:
        st.line_chart(display.set_index("step_label")["quality_score"])
    else:
        chart = (
            alt.Chart(display)
            .mark_line(point={"filled": True, "size": 95}, color="#1f9d63", strokeWidth=4)
            .encode(
                x=alt.X("step_label:N", title="Remediation step", sort=None),
                y=alt.Y(QUALITY_SCORE_FIELD, title="Quality score", scale=alt.Scale(domain=[0, 100])),
                tooltip=["step", "title", "quality_score", "checks_failed", "score_delta"],
            )
        )
        labels = chart.mark_text(align="center", baseline="bottom", dy=-12, color="#10243e").encode(
            text=alt.Text(QUALITY_SCORE_FIELD, format=".1f")
        )
        st.altair_chart(chart + labels, use_container_width=True)

    st.dataframe(
        display[["step", "title", "quality_score", "checks_failed", "score_delta"]],
        use_container_width=True,
        hide_index=True,
    )


def render_artifact_tags(artifacts: pd.DataFrame) -> None:
    if artifacts.empty:
        st.warning("No artifacts found for this run. Check that the runner completed and `reports/<run-id>/` exists.")
        return

    tags = "".join(f'<span class="artifact-tag">{row.artifact}</span>' for row in artifacts.itertuples(index=False))
    st.markdown(tags, unsafe_allow_html=True)


# ============================================================
# Top navigation bar (cross-app)
# ============================================================

NAV_TARGETS = [
    {"label": "Classic App",     "url": "http://localhost:18501",                          "kind": "self_classic"},
    {"label": "Kubernetes App",  "url": "http://127.0.0.1:28501",                          "kind": "self_k8s"},
    {"label": "Jenkins",         "url": "http://localhost:8080/job/data-quality-monitor-demo-e2e/", "kind": "platform"},
    {"label": "Argo CD",         "url": "https://127.0.0.1:28080",                         "kind": "platform"},
    {"label": "Grafana",         "url": "http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations", "kind": "platform"},
    {"label": "Prometheus",      "url": "http://localhost:9090/targets",                   "kind": "platform"},
    {"label": "SonarQube",       "url": "http://localhost:9000",                           "kind": "platform"},
]


def detect_current_app() -> str:
    """Return 'classic' or 'k8s' to mark 'you are here' in the navbar.

    Heuristic: the classic app is exposed on host port 18501, the K8s app on 28501.
    Inside the container, the Streamlit server listens on 8501. We use an env var
    set by the deploy/Helm chart to disambiguate; fall back to 'classic'.
    """
    flag = os.getenv("DQ_APP_PROFILE", "").strip().lower()
    if flag in ("classic", "k8s", "kubernetes"):
        return "k8s" if flag.startswith("k") else "classic"
    # Inside Kubernetes, the pod has a KUBERNETES_SERVICE_HOST set.
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return "k8s"
    return "classic"


def render_top_navbar() -> None:
    current = detect_current_app()
    parts = ['<div class="top-nav">',
             '<span class="top-nav-brand">DQ Control Tower</span>']
    for item in NAV_TARGETS:
        url = item["url"]
        label = item["label"]
        kind = item["kind"]
        css_class = ""
        prefix = ""
        if kind == "self_classic":
            if current == "classic":
                css_class = "you-are-here"
                prefix = '<span class="dot good"></span>'
                label = f"{label} (you are here)"
            else:
                css_class = "cross-app"
                prefix = '<span class="dot"></span>'
        elif kind == "self_k8s":
            if current == "k8s":
                css_class = "you-are-here"
                prefix = '<span class="dot good"></span>'
                label = f"{label} (you are here)"
            else:
                css_class = "cross-app"
                prefix = '<span class="dot"></span>'
        target_attr = "" if css_class == "you-are-here" else ' target="_blank" rel="noopener"'
        parts.append(
            f'<a class="{css_class}" href="{html.escape(url)}"{target_attr}>{prefix}{html.escape(label)}</a>'
        )
    parts.append(HTML_CLOSE_DIV)
    st.markdown("".join(parts), unsafe_allow_html=True)


# ============================================================
# Rules & Pipeline tab data sources
# ============================================================

RULES_PATH = ROOT_DIR / "config" / "rules.yml"
VALIDATORS_DIR = ROOT_DIR / "src" / "data_quality_monitor"
JENKINSFILE_PATH = ROOT_DIR / "Jenkinsfile"

VALIDATOR_DESCRIPTIONS = {
    "cli.py": "Command-line entrypoint. Parses --input / --rules / --output-dir and hands off to pipeline.",
    "pipeline.py": "Top-level orchestrator. Loads rules, reads the input file, runs validators, writes reports.",
    "config.py": "YAML loader. Parses config/rules.yml into a typed DataQualityRules object.",
    "data_loader.py": "Reads CSV or XLSX inputs into a pandas DataFrame.",
    VALIDATORS_MODULE_FILE: "The actual checks: required columns, non-null, uniqueness, dates, allowed values, null thresholds.",
    "report_generator.py": "Writes quality_report.csv, quality_report.xlsx, and summary.json with the per-check verdicts.",
    "models.py": "Typed dataclasses used across the validator (CheckResult, DataQualityRules, etc.).",
    "__main__.py": "Allows `python -m data_quality_monitor` to invoke the CLI.",
    "__init__.py": "Package marker. Exposes the public API surface.",
}


@st.cache_data(ttl=60, show_spinner=False)
def load_rules_definition() -> dict[str, object]:
    if yaml is None or not RULES_PATH.exists():
        return {}
    try:
        return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


@st.cache_data(ttl=60, show_spinner=False)
def parse_jenkinsfile_stages() -> list[dict[str, str]]:
    if not JENKINSFILE_PATH.exists():
        return []
    content = JENKINSFILE_PATH.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"stage\(['\"]([^'\"]+)['\"]\)", content)
    stage_blurbs = {
        "Checkout": "Pull the source tree (or skip if already checked out by the orchestrator).",
        "Validate Delivery Inputs": "Reject parameter combinations that would produce a broken release.",
        "Unit Tests": "Run pytest against the validator package.",
        "SonarQube Analysis": "Static code quality scan — advisory in the local demo.",
        "Data Quality Run": "Run the validator against the PSQ stress dataset, write reports.",
        "Stress Data Quality Matrix": "Run the validator across 8 dirty-data scenarios.",
        "Quality Improvement Ladder": "Apply 5 fixes in sequence and chart the score climbing.",
        "Helm Template Validation": "helm lint + helm template per environment values file.",
        "Terraform Validation": "terraform validate against the namespace bootstrap.",
        "Compute Image Metadata": "Decide the image tag for this build.",
        "Build Docker Image": "docker build — single artifact for runner + dashboard.",
        "Trivy Security Scan": "Scan the image for CVEs (advisory locally).",
        "Publish Docker Image": "Push to the registry with the computed tag.",
        "Update GitOps Repository": "Edit the target values file with the new image tag and push.",
        "Deploy With Ansible": "Idempotent Linux deploy via the bundled playbook (extra-vars via JSON file).",
        "Sync Argo CD Application": "Trigger Argo CD to reconcile the cluster against Git.",
        "Run Kubernetes Data Quality Job": "Force-create a Job from the CronJob and wait for completion.",
        "Smoke Test Classic": "Hit the Compose dashboard on :18501 and fail the build if it's not 200.",
        "Smoke Test Kubernetes": "Hit the K8s dashboard on :28501 and fail the build if it's not 200.",
    }
    return [
        {"index": f"{i:02d}", "name": name, "desc": stage_blurbs.get(name, "")}
        for i, name in enumerate(matches, start=1)
    ]


@st.cache_data(ttl=60, show_spinner=False)
def list_validator_modules() -> pd.DataFrame:
    if not VALIDATORS_DIR.exists():
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for module in sorted(VALIDATORS_DIR.glob("*.py")):
        line_count = sum(1 for _ in module.open("r", encoding="utf-8", errors="replace"))
        rows.append(
            {
                "module": module.name,
                "lines": line_count,
                "purpose": VALIDATOR_DESCRIPTIONS.get(module.name, ""),
                "path": module.relative_to(ROOT_DIR).as_posix(),
            }
        )
    return pd.DataFrame(rows)


def _rule_pill(text: str, css: str = "") -> str:
    return f'<span class="rule-pill {css}">{html.escape(str(text))}</span>'


def _null_threshold_css(pct: float) -> str:
    if pct >= 80:
        return "good"
    if pct >= 50:
        return "warn"
    return ""


def _render_rules_dataset_header(dataset: dict[str, object]) -> None:
    st.markdown(
        HTML_RULE_GROUP_OPEN
        + '<div class="rule-group-title">Dataset <span class="rule-group-sub">'
        + f'input → {html.escape(str(dataset.get("input_path", "")))} · '
        + f'output → {html.escape(str(dataset.get("output_dir", "")))}'
        + "</span></div>"
        + HTML_CLOSE_DIV,
        unsafe_allow_html=True,
    )


def _render_rules_column_section(title: str, items: list, blurb: str, css: str) -> None:
    pills = (
        "".join(_rule_pill(col, css) for col in items)
        if items
        else "<em style='color:#61758f;'>none configured</em>"
    )
    st.markdown(
        HTML_RULE_GROUP_OPEN
        + f'<div class="rule-group-title">{html.escape(title)} '
        + f'<span class="rule-group-sub">{html.escape(blurb)} · {len(items)} configured</span></div>'
        + f"<div>{pills}</div>"
        + HTML_CLOSE_DIV,
        unsafe_allow_html=True,
    )


def _render_allowed_values_section(allowed: dict) -> None:
    pieces = [
        HTML_RULE_GROUP_OPEN,
        '<div class="rule-group-title">Allowed values '
        f'<span class="rule-group-sub">{len(allowed)} columns gated</span></div>',
    ]
    for column, values in allowed.items():
        value_pills = "".join(_rule_pill(v, "good") for v in (values or []))
        pieces.append(
            f'<div style="margin-bottom:0.55rem;"><strong>{html.escape(column)}</strong><br>{value_pills}</div>'
        )
    pieces.append(HTML_CLOSE_DIV)
    st.markdown("".join(pieces), unsafe_allow_html=True)


def _render_null_thresholds_section(null_thresholds: dict) -> None:
    pieces = [
        HTML_RULE_GROUP_OPEN,
        '<div class="rule-group-title">Null-rate thresholds '
        f'<span class="rule-group-sub">{len(null_thresholds)} columns bounded</span></div>',
    ]
    for column, threshold in null_thresholds.items():
        pct = float(threshold) * 100 if isinstance(threshold, (int, float)) else 0.0
        pieces.append(_rule_pill(f"{column} ≤ {pct:.0f}% null", _null_threshold_css(pct)))
    pieces.append(HTML_CLOSE_DIV)
    st.markdown("".join(pieces), unsafe_allow_html=True)


def render_rules_panel(rules: dict[str, object]) -> None:
    if not rules:
        st.warning("Could not parse `config/rules.yml`. Open it directly to inspect the rule definitions.")
        return

    dataset = rules.get("dataset", {}) or {}
    checks = rules.get("checks", {}) or {}

    _render_rules_dataset_header(dataset)

    sections = [
        ("Required columns", checks.get("required_columns") or [], "Every column listed below must exist in the input file.", ""),
        ("Non-null columns", checks.get("non_null_columns") or [], "Critical fields — any null value triggers a FAIL.", "crit"),
        ("Unique business keys", checks.get("unique_columns") or [], "Duplicates trigger a FAIL.", "crit"),
        ("Parseable dates", checks.get("date_columns") or [], "Must parse as a calendar date.", ""),
    ]
    for title, items, blurb, css in sections:
        _render_rules_column_section(title, items, blurb, css)

    allowed = checks.get("allowed_values") or {}
    if allowed:
        _render_allowed_values_section(allowed)

    null_thresholds = checks.get("null_thresholds") or {}
    if null_thresholds:
        _render_null_thresholds_section(null_thresholds)


def render_pipeline_stages_panel() -> None:
    stages = parse_jenkinsfile_stages()
    if not stages:
        st.info("No `Jenkinsfile` found to parse.")
        return
    st.markdown(
        f'<div class="rule-group-title">Jenkins pipeline stages '
        f'<span class="rule-group-sub">{len(stages)} stages, parsed from `Jenkinsfile`</span></div>',
        unsafe_allow_html=True,
    )
    rows_html = [HTML_RULE_GROUP_OPEN]
    for stage in stages:
        rows_html.append(
            '<div class="stage-row">'
            f'<div class="stage-num">{html.escape(stage["index"])}</div>'
            f'<div><div class="stage-name">{html.escape(stage["name"])}</div>'
            f'<div class="stage-desc">{html.escape(stage["desc"])}</div></div>'
            + HTML_CLOSE_DIV
        )
    rows_html.append(HTML_CLOSE_DIV)
    st.markdown("".join(rows_html), unsafe_allow_html=True)


def render_validator_modules_panel() -> None:
    modules = list_validator_modules()
    if modules.empty:
        st.info("Validator package not found.")
        return
    st.markdown(
        '<div class="rule-group-title">Python validator modules '
        f'<span class="rule-group-sub">{len(modules)} files in `src/data_quality_monitor/`</span></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(modules, use_container_width=True, hide_index=True)


# ============================================================
# Source-code viewer
# ============================================================

SOURCE_VIEWER_GROUPS: list[tuple[str, list[tuple[str, Path, str]]]] = [
    (
        "Data processing (Python)",
        [
            ("src/main.py", ROOT_DIR / "src" / "main.py", "python"),
            ("src/data_quality_monitor/__main__.py", VALIDATORS_DIR / "__main__.py", "python"),
            ("src/data_quality_monitor/cli.py", VALIDATORS_DIR / "cli.py", "python"),
            ("src/data_quality_monitor/pipeline.py", VALIDATORS_DIR / "pipeline.py", "python"),
            (f"src/data_quality_monitor/{VALIDATORS_MODULE_FILE}", VALIDATORS_DIR / VALIDATORS_MODULE_FILE, "python"),
            ("src/data_quality_monitor/config.py", VALIDATORS_DIR / "config.py", "python"),
            ("src/data_quality_monitor/data_loader.py", VALIDATORS_DIR / "data_loader.py", "python"),
            ("src/data_quality_monitor/report_generator.py", VALIDATORS_DIR / "report_generator.py", "python"),
            ("src/data_quality_monitor/models.py", VALIDATORS_DIR / "models.py", "python"),
        ],
    ),
    (
        "Rules & inputs",
        [
            ("config/rules.yml", ROOT_DIR / "config" / "rules.yml", "yaml"),
        ],
    ),
    (
        "Orchestration",
        [
            ("Jenkinsfile", JENKINSFILE_PATH, "groovy"),
            ("Dockerfile", ROOT_DIR / "Dockerfile", "dockerfile"),
            (DOCKER_COMPOSE_FILE, ROOT_DIR / DOCKER_COMPOSE_FILE, "yaml"),
        ],
    ),
    (
        "Deployment (Ansible + Helm)",
        [
            ("ansible/playbook.yml", ROOT_DIR / "ansible" / "playbook.yml", "yaml"),
            ("ansible/roles/app_deploy/tasks/main.yml",
             ROOT_DIR / "ansible" / "roles" / "app_deploy" / "tasks" / "main.yml", "yaml"),
            ("helm/.../values.yaml",
             ROOT_DIR / "helm" / "data-quality-monitor" / "values.yaml", "yaml"),
            ("helm/.../templates/deployment.yaml",
             ROOT_DIR / "helm" / "data-quality-monitor" / "templates" / "deployment.yaml", "yaml"),
            ("helm/.../templates/cronjob.yaml",
             ROOT_DIR / "helm" / "data-quality-monitor" / "templates" / "cronjob.yaml", "yaml"),
        ],
    ),
]


def render_source_code_viewer() -> None:
    st.markdown("#### Source-Code Viewer")
    st.caption(
        "Pick a file from the repository to read its source. Read-only — files load straight off disk."
    )

    # Flatten and filter to files that actually exist.
    options: list[tuple[str, str, Path, str]] = []
    for group, items in SOURCE_VIEWER_GROUPS:
        for label, path, language in items:
            if path.exists():
                options.append((group, label, path, language))

    if not options:
        st.info("No source files found at the expected paths.")
        return

    labels = [f"{group} — {label}" for group, label, _, _ in options]
    default_index = next(
        (i for i, (_, label, _, _) in enumerate(options) if label.endswith(VALIDATORS_MODULE_FILE)),
        0,
    )
    chosen_label = st.selectbox("File", labels, index=default_index, key="source_code_viewer_file")
    _, _, chosen_path, chosen_language = options[labels.index(chosen_label)]

    try:
        content = chosen_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        st.error(f"Could not read `{chosen_path.as_posix()}`: {error}")
        return

    line_count = content.count("\n") + 1
    size_kb = chosen_path.stat().st_size / 1024
    st.caption(
        f"`{chosen_path.relative_to(ROOT_DIR).as_posix()}` · {line_count} lines · {size_kb:.1f} KB"
    )
    st.code(content, language=chosen_language)


# ============================================================
# Data Browser tab
# ============================================================

def _human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} GB"


@st.cache_data(ttl=30, show_spinner=False)
def load_input_full(input_value: str | None, max_rows: int = 1000) -> pd.DataFrame:
    if not input_value:
        return pd.DataFrame()
    input_path = Path(str(input_value))
    if not input_path.is_absolute():
        input_path = ROOT_DIR / input_path
    if not input_path.exists() or input_path.suffix.lower() != ".csv":
        return pd.DataFrame()
    return pd.read_csv(input_path, nrows=max_rows)


def render_data_browser_panel(
    summary: dict[str, object],
    report: pd.DataFrame,
    selected_run,
) -> None:
    st.subheader("Pipeline output — `quality_report.csv`")
    st.caption(
        f"This is the per-check verdict table the validator wrote for run "
        f"`{selected_run.run_id}`. Filter by column to drill into what failed."
    )

    if report.empty:
        st.warning("Quality report is empty for this run.")
        return

    columns = [c for c in ["status", "severity", "check_name", "column_name"] if c in report.columns]
    filtered = report.copy()
    filter_cols = st.columns(max(len(columns), 1))
    for index, column_name in enumerate(columns):
        with filter_cols[index]:
            values = sorted(filtered[column_name].dropna().astype(str).unique().tolist())
            selected = st.multiselect(
                column_name,
                values,
                default=values,
                key=f"data_browser_filter_{column_name}",
            )
            if selected:
                filtered = filtered[filtered[column_name].astype(str).isin(selected)]

    search = st.text_input("Search message text", "", key="data_browser_search")
    if search and "message" in filtered.columns:
        filtered = filtered[filtered["message"].astype(str).str.contains(search, case=False, na=False)]

    info_cols = st.columns(4)
    info_cols[0].metric("Rows shown", len(filtered))
    info_cols[1].metric("Total rows", len(report))
    fail_count = int((filtered.get("status", pd.Series(dtype=str)) == "FAIL").sum()) if "status" in filtered else 0
    info_cols[2].metric("FAIL in view", fail_count)
    info_cols[3].metric("PASS in view", len(filtered) - fail_count)

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"quality_report_filtered_{selected_run.run_id.replace('/', '_')}.csv",
        mime="text/csv",
    )

    st.markdown("---")
    st.subheader("Pipeline input — first 1,000 rows of the source CSV")
    input_value = summary.get("input_file")
    if isinstance(input_value, str):
        st.caption(f"`{input_value}` · trimmed for browser performance")
    input_df = load_input_full(input_value if isinstance(input_value, str) else None)
    if input_df.empty:
        st.info("Input CSV not available from the dashboard runtime.")
    else:
        col_search = st.text_input(
            "Filter rows where any cell contains…",
            "",
            key="data_browser_input_search",
        )
        view = input_df
        if col_search:
            mask = view.astype(str).apply(lambda s: s.str.contains(col_search, case=False, na=False)).any(axis=1)
            view = view[mask]
        st.caption(f"{len(view)} of {len(input_df)} preview rows match")
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Raw summary JSON")
    st.json(summary)


# ============================================================
# Notebook viewer
# ============================================================

NOTEBOOK_SEARCH_PATHS = [
    ROOT_DIR / "notebooks",
    ROOT_DIR / "data",
    ROOT_DIR,
]


@st.cache_data(ttl=60, show_spinner=False)
def discover_notebooks() -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for base in NOTEBOOK_SEARCH_PATHS:
        if not base.exists():
            continue
        for nb_path in base.rglob("*.ipynb"):
            if any(part.startswith(".") for part in nb_path.parts):
                continue
            resolved = nb_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(nb_path)
    return found


def _coerce_text(value: object) -> str:
    if isinstance(value, list):
        return "".join(value)
    return value if isinstance(value, str) else ""


def _render_notebook_cell_output(output: dict) -> None:
    output_type = output.get("output_type")
    if output_type == "stream":
        st.code(_coerce_text(output.get("text", "")), language="text")
    elif output_type in ("execute_result", "display_data"):
        data = output.get("data", {}) or {}
        if "text/plain" in data:
            st.code(_coerce_text(data["text/plain"]), language="text")
    elif output_type == "error":
        st.error("\n".join(output.get("traceback", [])))


def _render_notebook_cell(cell: dict, index: int, show_outputs: bool) -> None:
    cell_type = cell.get("cell_type")
    source = _coerce_text(cell.get("source", ""))
    if cell_type == "markdown":
        st.markdown(source, unsafe_allow_html=False)
        return
    if cell_type == "raw":
        st.code(source, language="text")
        return
    if cell_type != "code":
        return

    st.markdown(f"**In [{index}]**")
    st.code(source, language="python")
    if show_outputs:
        for output in cell.get("outputs", []) or []:
            _render_notebook_cell_output(output)


def _pick_notebook() -> Path | None:
    notebooks = discover_notebooks()
    if not notebooks:
        st.info(
            "No `.ipynb` files found in `notebooks/`, `data/`, or the project root. "
            "Drop the source notebook (e.g. `PSQ_customer_base_v8.ipynb`) into `notebooks/` "
            "and refresh — its cells will render here."
        )
        return None

    labels = [nb.relative_to(ROOT_DIR).as_posix() for nb in notebooks]
    chosen = st.selectbox("Notebook", labels, key="notebook_viewer_selection")
    return notebooks[labels.index(chosen)]


DB_PATH = ROOT_DIR / "data" / "db" / "dq.db"


RISK_SEVERITY_ORDER = ["Low", "Medium", "High", "VeryHigh"]


@st.cache_data(ttl=30, show_spinner=False)
def load_ricos_tables() -> dict[str, pd.DataFrame | str | None]:
    """Read every analytics_* output table from the SQL pipeline.

    Returns empty frames when the DB file is absent so the panel can render a
    friendly empty state instead of crashing.
    """
    if not DB_PATH.exists():
        return {
            "summary": pd.DataFrame(),
            "rich": pd.DataFrame(),
            "flag": pd.DataFrame(),
            "generated_at": None,
        }

    import sqlite3

    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        summary = pd.read_sql_query(
            "SELECT source, in_ricos_flag, merchants, active_merchants, pct_of_source "
            "FROM analytics_psq_match_summary ORDER BY source, in_ricos_flag",
            con,
        )
        rich = pd.read_sql_query(
            "SELECT source, id, name, country, in_ricos_flag, ricos_risk_score, ricos_risk_label, "
            "ricos_screening_status, ricos_watchlist_hit_pct, ricos_watchlist_list, "
            "ricos_pep_hit_pct, ricos_ubo_count, ricos_si_count, ricos_next_review_date "
            "FROM analytics_psq_with_ricos_rich",
            con,
        )
        flag_counts = pd.read_sql_query(
            "SELECT in_ricos_flag, COUNT(*) AS merchants FROM analytics_psq_with_ricos_flag "
            "GROUP BY in_ricos_flag",
            con,
        )
        generated_row = pd.read_sql_query(
            "SELECT MAX(generated_at) AS generated_at FROM analytics_psq_match_summary",
            con,
        )
    finally:
        con.close()
    generated_at = generated_row["generated_at"].iloc[0] if not generated_row.empty else None
    return {"summary": summary, "rich": rich, "flag": flag_counts, "generated_at": generated_at}


def render_ricos_panel() -> None:
    st.subheader("RICOS Coverage")
    st.caption(
        "Live read from the SQL pipeline output tables (`analytics_psq_match_summary`, "
        "`analytics_psq_with_ricos_rich`, `analytics_psq_with_ricos_flag`). Run "
        "`python scripts/data/run_sql_pipeline.py --reset` to refresh."
    )

    tables = load_ricos_tables()
    summary = tables["summary"]
    rich = tables["rich"]
    generated_at = tables.get("generated_at")

    if summary.empty:
        st.warning(
            f"No SQL pipeline output found at `{DB_PATH.relative_to(ROOT_DIR).as_posix()}`. "
            "Run `python scripts/data/run_sql_pipeline.py --reset` to generate it."
        )
        return

    if generated_at:
        ts = pd.to_datetime(generated_at, errors="coerce")
        if pd.notna(ts):
            st.caption(f"**SQL pipeline last ran:** {ts.strftime('%Y-%m-%d %H:%M')} UTC")
        else:
            st.caption(f"**SQL pipeline last ran:** {generated_at}")

    total = int(rich.shape[0])
    in_ricos = int((rich["in_ricos_flag"] == "Y").sum())
    not_in_ricos = total - in_ricos
    pct = (in_ricos / total * 100) if total else 0.0
    matched = rich[rich["in_ricos_flag"] == "Y"]
    high_risk = int(matched["ricos_risk_score"].isin(["High", "VeryHigh"]).sum())
    watchlist_hits = int(matched["ricos_watchlist_hit_pct"].notna().sum())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total merchants", f"{total:,}")
    col2.metric("In RICOS (Y)", f"{in_ricos:,}", f"{pct:.1f}%")
    col3.metric("Not in RICOS (N)", f"{not_in_ricos:,}", f"{100 - pct:.1f}%")
    col4.metric("High / VeryHigh risk", f"{high_risk:,}")
    col5.metric("Watchlist hits", f"{watchlist_hits:,}", help="Merchants with a non-null OFAC/EU/UN/World-Check hit %.")

    st.markdown("#### Match rates by source")
    st.caption("Notebook contract: WAY4 ~71.4%, PASS ~35.3%. Hit on every run.")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    matched_only = summary[summary["in_ricos_flag"] == "Y"][["source", "pct_of_source"]]
    match_chart = (
        alt.Chart(matched_only)
        .mark_bar()
        .encode(
            x=alt.X("source:N", title="Source", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "pct_of_source:Q",
                title="% in RICOS",
                scale=alt.Scale(domain=[0, 100]),
            ),
            tooltip=["source", alt.Tooltip("pct_of_source:Q", title="% in RICOS", format=".2f")],
        )
        .properties(height=200)
    )
    st.altair_chart(match_chart, use_container_width=True)

    st.markdown("#### Risk distribution")
    risk_counts = (
        matched["ricos_risk_score"].value_counts().rename_axis("risk").reset_index(name="merchants")
    )
    # Sort by severity, not alphabetical.
    risk_counts["risk"] = pd.Categorical(risk_counts["risk"], categories=RISK_SEVERITY_ORDER, ordered=True)
    risk_counts = risk_counts.sort_values("risk").reset_index(drop=True)

    risk_col_a, risk_col_b = st.columns([1, 1])
    with risk_col_a:
        st.dataframe(risk_counts, use_container_width=True, hide_index=True)
    with risk_col_b:
        risk_chart = (
            alt.Chart(risk_counts.assign(risk=risk_counts["risk"].astype(str)))
            .mark_bar()
            .encode(
                x=alt.X("risk:N", title="Risk class", sort=RISK_SEVERITY_ORDER, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("merchants:Q", title="Merchants"),
                tooltip=["risk", "merchants"],
            )
            .properties(height=240)
        )
        st.altair_chart(risk_chart, use_container_width=True)

    st.markdown("#### Watchlist hits")
    hits = (
        matched[matched["ricos_watchlist_hit_pct"].notna()]
        [["id", "name", "country", "ricos_risk_score", "ricos_watchlist_list", "ricos_watchlist_hit_pct"]]
        .sort_values("ricos_watchlist_hit_pct", ascending=False)
        .head(10)
    )
    if hits.empty:
        st.info("No watchlist hits in the current run.")
    else:
        st.dataframe(hits, use_container_width=True, hide_index=True)

    with st.expander("Drill down — filter by source / risk / in-RICOS", expanded=False):
        source_filter = st.multiselect("Source", sorted(rich["source"].unique()), default=list(sorted(rich["source"].unique())))
        risk_filter = st.multiselect(
            "Risk", sorted(rich["ricos_risk_score"].dropna().unique()),
            default=list(sorted(rich["ricos_risk_score"].dropna().unique())),
        )
        in_ricos_filter = st.radio("In RICOS", ["All", "Y", "N"], horizontal=True, index=0)

        filtered = rich[rich["source"].isin(source_filter)]
        if in_ricos_filter != "All":
            filtered = filtered[filtered["in_ricos_flag"] == in_ricos_filter]
        if risk_filter:
            filtered = filtered[
                filtered["ricos_risk_score"].isin(risk_filter) | filtered["ricos_risk_score"].isna()
            ]
        st.caption(f"{len(filtered):,} rows matching filters")
        st.dataframe(filtered.head(500), use_container_width=True, hide_index=True)


def render_notebook_panel() -> None:
    st.subheader("Source notebook")
    if nbformat is None:
        st.warning(
            "`nbformat` is not installed in this dashboard runtime — the notebook viewer is disabled. "
            "Add `nbformat>=5.10` to `requirements.txt` and rebuild the image."
        )
        return

    nb_path = _pick_notebook()
    if nb_path is None:
        return

    try:
        nb = nbformat.read(nb_path, as_version=4)
    except (OSError, ValueError, nbformat.reader.NotJSONError) as error:
        st.error(f"Could not parse `{nb_path.relative_to(ROOT_DIR).as_posix()}`: {error}")
        return

    metadata = nb.get("metadata") or {}
    kernel = (metadata.get("kernelspec") or {}).get("display_name", "unknown kernel")
    st.caption(
        f"`{nb_path.relative_to(ROOT_DIR).as_posix()}` · {len(nb.cells)} cells · kernel: {kernel} · "
        f"{_human_size(nb_path.stat().st_size)}"
    )

    show_outputs = st.toggle("Show cell outputs", value=False, key="notebook_show_outputs")
    for index, cell in enumerate(nb.cells, start=1):
        _render_notebook_cell(cell, index, show_outputs)


st.set_page_config(page_title="Data Quality Control Tower", layout="wide", initial_sidebar_state="expanded")
inject_styles()
render_top_navbar()

runs = discover_runs()

current_profile = detect_current_app()
kicker_text = "DevOps Demo Surface · Classic (Ansible) Deploy" if current_profile == "classic" else "DevOps Demo Surface · Kubernetes (GitOps) Deploy"

hero_html = (
    '<div class="hero-panel">'
    + html_div("hero-kicker", kicker_text)
    + '<h1 class="hero-title">Data Quality Control Tower</h1>'
    + '<p class="hero-copy">'
    + "One visual place for data quality, CI results, deployment capability, artifacts, and platform evidence. "
    + "An operations cockpit, not a CSV viewer."
    + "</p>"
    + HTML_CLOSE_DIV
)
st.markdown(hero_html, unsafe_allow_html=True)

if runs.empty:
    st.warning("No reports yet. Run `.\\scripts\\demo_full.ps1` or trigger a Jenkins pipeline, then refresh.")
    st.stop()

run_lookup = {row.label: row for row in runs.itertuples(index=False)}
with st.sidebar:
    st.header("Run Selector")
    selected_label = st.selectbox(
        "Choose a generated run",
        list(run_lookup.keys()),
        help="Pick a run here to drive every panel on the right. The inventory below is read-only.",
    )
    selected_run = run_lookup[selected_label]

    with st.expander("Run inventory (read-only)", expanded=False):
        st.caption("Snapshot of every report folder discovered on disk. Use the dropdown above to switch runs.")
        st.dataframe(
            runs[["run_id", "quality_score", "checks_failed", "generated_at"]].assign(
                generated_at=lambda df: df["generated_at"].dt.tz_convert(LOCAL_TIMEZONE).dt.strftime("%d %b %Y %H:%M")
            ),
            use_container_width=True,
            hide_index=True,
        )

summary = load_summary(Path(selected_run.summary_path))
report = load_report(Path(selected_run.report_path))
artifacts = build_artifact_inventory(Path(selected_run.summary_path).parent)
capabilities = build_capability_table()
remediation = build_remediation_plan(report)
input_sample = load_input_sample(summary)
quality_ladder = load_quality_ladder_summary()

score = float(summary["quality_score"])
checks_failed = int(summary["checks_failed"])
checks_passed = int(summary["checks_passed"])
rows = int(summary["row_count"])
generated_local = pd.to_datetime(summary["generated_at_utc"], utc=True).tz_convert(LOCAL_TIMEZONE).strftime("%d %b %Y %H:%M:%S")
capability_count = int((capabilities["status"] == "Configured").sum())

top_cols = st.columns(5)
with top_cols[0]:
    render_signal_card("Quality Score", f"{score:.0f}%", "Overall health of the selected validation run")
with top_cols[1]:
    render_signal_card("Failed Checks", str(checks_failed), "Controls that require remediation")
with top_cols[2]:
    render_signal_card("Passed Checks", str(checks_passed), "Rules that already comply")
with top_cols[3]:
    render_signal_card("Rows Processed", str(rows), "Rows inspected in the selected dataset")
with top_cols[4]:
    render_signal_card("DevOps Assets", str(capability_count), "Platform capabilities configured (CI, security, monitoring, GitOps, etc.)")

st.progress(min(max(score / 100.0, 0.0), 1.0), text=f"Current quality score: {score:.1f}%")
st.caption(f"Selected run: `{selected_run.run_id}` generated on `{generated_local}`")

overview_tab, issues_tab, data_browser_tab, ricos_tab, pipeline_tab, artifacts_tab, platform_tab = st.tabs(
    ["Overview", "Issues", "Data Browser", "RICOS Coverage", "Pipeline & Rules", "Artifacts", "DevOps Footprint"]
)

with overview_tab:
    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        with st.container(border=False):
            st.subheader("Pass vs Fail Split")
            render_pass_fail_chart(summary)
    with right:
        with st.container(border=False):
            st.subheader("Quality Score Trend")
            render_trend_chart(runs)

    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        st.subheader("Failed Rows by Control")
        render_failed_rows_chart(report)
    with chart_right:
        st.subheader("Run Summary")
        severity_summary = (
            report.assign(metric_value=pd.to_numeric(report["metric_value"], errors="coerce").fillna(0))
            .groupby(["status", "severity"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["status", "severity"])
        )
        st.dataframe(severity_summary, use_container_width=True, hide_index=True)

    st.subheader("Quality Improvement Ladder")
    render_quality_ladder_chart(quality_ladder)

    st.subheader("Delivery Chain")
    render_flow_strip()

    if not input_sample.empty:
        with st.expander("Input Dataset Snapshot", expanded=False):
            st.dataframe(input_sample, use_container_width=True, hide_index=True)

with issues_tab:
    render_remediation_plan(remediation)
    st.subheader("Failed Controls")
    failed_checks = report[report["status"] == "FAIL"].copy()
    if failed_checks.empty:
        st.success("All controls passed in this run.")
    else:
        failed_checks["failed_rows"] = pd.to_numeric(failed_checks["failed_rows"], errors="coerce").fillna(0).astype(int)
        failed_checks["metric_value"] = pd.to_numeric(failed_checks["metric_value"], errors="coerce").fillna(0)
        st.dataframe(
            failed_checks[
                ["check_name", "column_name", "severity", "metric_value", "threshold", "failed_rows", "message"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Full Validation Report", expanded=False):
        st.dataframe(report, use_container_width=True, hide_index=True)

    with st.expander("Raw Summary JSON", expanded=False):
        st.json(summary)

with data_browser_tab:
    render_data_browser_panel(summary, report, selected_run)

with ricos_tab:
    render_ricos_panel()

with pipeline_tab:
    st.subheader("How the data is processed")
    st.caption(
        "Everything below is read directly from the repository on disk — the rules the validator enforces, "
        "the Python modules that implement them, and the Jenkins stages that orchestrate the pipeline. "
        "This tab gives you the 'how' behind the numbers on the Overview tab."
    )

    rules_def = load_rules_definition()
    rules_col, modules_col = st.columns([1.15, 0.85], gap="large")

    with rules_col:
        st.markdown("#### Active Validation Rules")
        st.caption(f"Source: `{RULES_PATH.relative_to(ROOT_DIR).as_posix()}` · live read")
        render_rules_panel(rules_def)

    with modules_col:
        st.markdown("#### Validator Code")
        st.caption(f"Source: `{VALIDATORS_DIR.relative_to(ROOT_DIR).as_posix()}/` · live read")
        render_validator_modules_panel()

    st.markdown("---")
    st.markdown("#### Pipeline Stages")
    st.caption(f"Source: `{JENKINSFILE_PATH.name}` · parsed at load time")
    render_pipeline_stages_panel()

    with st.expander("Raw `rules.yml`", expanded=False):
        if RULES_PATH.exists():
            st.code(RULES_PATH.read_text(encoding="utf-8"), language="yaml")
        else:
            st.warning("`config/rules.yml` not found.")

    st.markdown("---")
    render_source_code_viewer()

    st.markdown("---")
    render_notebook_panel()

with artifacts_tab:
    st.subheader("Generated Artifacts")
    render_artifact_tags(artifacts)
    render_artifact_downloads(artifacts)
    st.dataframe(artifacts, use_container_width=True, hide_index=True)

    artifact_cols = st.columns(3)
    for index, row in enumerate(artifacts.itertuples(index=False)):
        with artifact_cols[index % 3]:
            render_signal_card(row.artifact, f"{row.size_kb} KB", row.modified_at)

with platform_tab:
    render_platform_health()
    render_platform_links()
    st.subheader("Configured DevOps Surface")
    render_capability_cards(capabilities)

    environment_rows = pd.DataFrame(
        [
            {
                "environment": "dev",
                "terraform": (ROOT_DIR / "terraform" / "environments" / "dev" / MAIN_TF_FILENAME).exists(),
                "argocd": (ROOT_DIR / "argocd" / "app-dev.yaml").exists(),
                "helm_values": (ROOT_DIR / "helm" / "data-quality-monitor" / "values-dev.yaml").exists(),
            },
            {
                "environment": "staging",
                "terraform": (ROOT_DIR / "terraform" / "environments" / "staging" / MAIN_TF_FILENAME).exists(),
                "argocd": (ROOT_DIR / "argocd" / "app-staging.yaml").exists(),
                "helm_values": (ROOT_DIR / "helm" / "data-quality-monitor" / "values-staging.yaml").exists(),
            },
            {
                "environment": "prod",
                "terraform": (ROOT_DIR / "terraform" / "environments" / "prod" / MAIN_TF_FILENAME).exists(),
                "argocd": (ROOT_DIR / "argocd" / "app-prod.yaml").exists(),
                "helm_values": (ROOT_DIR / "helm" / "data-quality-monitor" / "values-prod.yaml").exists(),
            },
        ]
    )
    environment_rows[["terraform", "argocd", "helm_values"]] = environment_rows[
        ["terraform", "argocd", "helm_values"]
    ].replace({True: "Ready", False: "Missing"})

    st.subheader("Environment Readiness")
    st.dataframe(environment_rows, use_container_width=True, hide_index=True)
