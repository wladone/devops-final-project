"""Validate the Helm chart with ``helm lint`` + ``helm template``.

When ``kubeconform`` is also available, the rendered manifests are piped
through it for schema validation.
"""

from __future__ import annotations

import shutil

import pytest

from tests.infra._helpers import require, run

pytestmark = pytest.mark.infra

CHART = "helm/data-quality-monitor"


@pytest.mark.parametrize(
    "values_file",
    [
        "helm/data-quality-monitor/values.yaml",
        "helm/data-quality-monitor/values-dev.yaml",
        "helm/data-quality-monitor/values-prod.yaml",
    ],
)
def test_helm_lint(values_file: str) -> None:
    helm = require("helm")
    result = run([helm, "lint", CHART, "-f", values_file])
    assert result.returncode == 0, f"helm lint failed:\n{result.stdout}\n{result.stderr}"


def test_helm_template_renders_with_prod_values() -> None:
    helm = require("helm")
    result = run([helm, "template", "dqm", CHART, "-f", f"{CHART}/values-prod.yaml"])
    assert result.returncode == 0, f"helm template failed:\n{result.stderr}"
    assert "kind: Deployment" in result.stdout or "kind: StatefulSet" in result.stdout


def test_rendered_manifests_pass_kubeconform() -> None:
    if not shutil.which("kubeconform"):
        pytest.skip("kubeconform is not installed")
    helm = require("helm")
    render = run([helm, "template", "dqm", CHART, "-f", f"{CHART}/values-prod.yaml"])
    assert render.returncode == 0
    # Pipe stdout into kubeconform via a temporary file to keep the test
    # cross-platform (no shell pipelines).
    import tempfile
    from pathlib import Path
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(render.stdout)
        manifest_path = Path(f.name)
    try:
        check = run(["kubeconform", "-strict", "-summary", str(manifest_path)])
        assert check.returncode == 0, check.stdout + check.stderr
    finally:
        manifest_path.unlink(missing_ok=True)
