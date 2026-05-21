"""Dry-run ``argocd app diff --local`` against the chart.

This only runs when both the ``argocd`` CLI is installed AND an
``ARGOCD_SERVER`` env var is set, since the diff needs cluster state.
Otherwise it skips so local runs stay green.
"""

from __future__ import annotations

import os

import pytest

from tests.infra._helpers import require, run

pytestmark = pytest.mark.infra


def test_argocd_app_diff_clean() -> None:
    if not os.environ.get("ARGOCD_SERVER"):
        pytest.skip("ARGOCD_SERVER not set — running diff requires cluster context")
    argocd = require("argocd")
    app = os.environ.get("ARGOCD_APP", "data-quality-monitor")
    result = run([argocd, "app", "diff", app, "--local", "helm/data-quality-monitor"])
    # Exit code 1 means "diff found", exit code 0 means clean.
    assert result.returncode in (0, 1), result.stderr
    if result.returncode == 1:
        pytest.fail(f"ArgoCD app {app} has drift:\n{result.stdout}")
