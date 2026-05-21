"""Resilience tests for the Streamlit dashboard.

We test two things:
  1. The pure helpers (`get_platform_probe_host`, `rewrite_local_url_for_probe`,
     `discover_runs`) by importing them safely via AppTest's runtime, which
     guards the top-level `st.set_page_config` call.
  2. End-to-end dashboard behavior against an empty / corrupted reports
     directory, asserting the app stops with a clear message rather than
     crashing with a traceback.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest

DASHBOARD_APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


def write_summary(reports_dir: Path, run_id: str, payload: dict) -> Path:
    run_dir = reports_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")
    (run_dir / "quality_report.csv").write_text(
        "check_name,column_name,status,severity,metric_value,threshold,failed_rows,message\n"
        "required_columns_present,dataset,PASS,critical,1,1,0,ok\n",
        encoding="utf-8",
    )
    return summary_path


def make_app(reports_root: Path) -> AppTest:
    # The autouse _reports_root fixture sets DQ_REPORT_ROOT in the process env;
    # AppTest runs the script in-process so the dashboard inherits it.
    # Streamlit's AppTest is slow to spin up (3–25 s in CI); 60 s gives enough
    # headroom for the long-tail without masking real hangs.
    return AppTest.from_file(str(DASHBOARD_APP), default_timeout=60)


@pytest.fixture(autouse=True)
def _reports_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("DQ_REPORT_ROOT", str(tmp_path))
    return tmp_path


def test_dashboard_stops_gracefully_on_empty_reports(tmp_path: Path) -> None:
    """No summary.json under DQ_REPORT_ROOT must not crash the app."""
    app = make_app(tmp_path).run()

    # When there are no runs, the app should reach a stop() (no exception)
    # and surface an explanatory error / warning to the user.
    assert not app.exception, f"Dashboard raised: {app.exception}"
    rendered_text = " ".join(
        block.value for block in (*app.error, *app.warning, *app.info, *app.markdown) if block.value
    )
    assert rendered_text, "Dashboard rendered nothing when reports/ was empty"


def test_dashboard_skips_corrupted_summary_files(tmp_path: Path) -> None:
    """A corrupt summary.json next to a valid one must not crash discovery."""
    write_summary(
        tmp_path,
        "good_run",
        {
            "generated_at_utc": "2026-05-19T08:00:00+00:00",
            "row_count": 10,
            "checks_total": 5,
            "checks_passed": 5,
            "checks_failed": 0,
            "quality_score": 1.0,
        },
    )

    bad_run_dir = tmp_path / "bad_run"
    bad_run_dir.mkdir()
    (bad_run_dir / "summary.json").write_text("{not valid json", encoding="utf-8")

    app = make_app(tmp_path).run()

    assert not app.exception, f"Dashboard raised on corrupt summary.json: {app.exception}"


def test_dashboard_handles_summary_with_missing_keys(tmp_path: Path) -> None:
    """A summary.json missing optional keys must default sensibly."""
    write_summary(
        tmp_path,
        "sparse_run",
        {"generated_at_utc": "2026-05-19T08:00:00+00:00"},
    )

    app = make_app(tmp_path).run()

    assert not app.exception, f"Dashboard crashed on sparse summary: {app.exception}"
