"""Lint the project Dockerfile with ``hadolint``."""

from __future__ import annotations

import pytest

from tests.infra._helpers import require, run

pytestmark = pytest.mark.infra


def test_hadolint_passes() -> None:
    hadolint = require("hadolint")
    # Trivyignore-equivalent rules can be configured via .hadolint.yaml at
    # the repo root if needed; absence == defaults.
    result = run([hadolint, "Dockerfile"])
    assert result.returncode == 0, f"hadolint findings:\n{result.stdout}"


def test_dockerignore_present_and_excludes_secrets() -> None:
    from tests.infra._helpers import REPO_ROOT
    dockerignore = REPO_ROOT / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore is missing — secrets risk"
    content = dockerignore.read_text(encoding="utf-8")
    for must_ignore in (".git", ".env"):
        assert must_ignore in content, f"{must_ignore!r} not in .dockerignore"
