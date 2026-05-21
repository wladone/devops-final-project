"""Validate Terraform formatting + syntax for each environment.

We avoid running ``terraform init`` (which hits the network for providers);
``-backend=false`` lets us validate against any provider stubs that are
already cached, and skips when nothing is.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.infra._helpers import REPO_ROOT, require, run

pytestmark = pytest.mark.infra

ENVIRONMENTS = ["dev", "lab", "prod", "staging"]


def test_terraform_fmt_check() -> None:
    terraform = require("terraform")
    result = run([terraform, "fmt", "-recursive", "-check", "terraform"])
    assert result.returncode == 0, (
        f"terraform fmt reports unformatted files:\n{result.stdout}"
    )


@pytest.mark.parametrize("env", ENVIRONMENTS)
def test_terraform_validate(env: str) -> None:
    terraform = require("terraform")
    env_dir: Path = REPO_ROOT / "terraform" / "environments" / env
    if not (env_dir / ".terraform").exists():
        # validate without providers cached → init -backend=false first.
        init = run([terraform, "init", "-backend=false", "-input=false"], cwd=env_dir)
        if init.returncode != 0:
            pytest.skip(
                f"terraform init failed for {env} (likely offline / no provider "
                f"cache): {init.stderr.splitlines()[-1] if init.stderr else ''}"
            )
    result = run([terraform, "validate"], cwd=env_dir)
    assert result.returncode == 0, result.stdout + result.stderr
