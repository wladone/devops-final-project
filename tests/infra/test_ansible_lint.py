"""Run ``ansible-lint`` against the playbook tree.

Skipped when the binary isn't installed locally; CI must install it so
this gates merges."""

from __future__ import annotations

import pytest

from tests.infra._helpers import REPO_ROOT, require, run

pytestmark = pytest.mark.infra


def test_ansible_lint_passes() -> None:
    lint = require("ansible-lint")
    result = run([lint, "--offline", "ansible/playbook.yml"])
    assert result.returncode == 0, (
        f"ansible-lint reported issues:\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_ansible_syntax_check() -> None:
    ansible_playbook = require("ansible-playbook")
    result = run(
        [ansible_playbook, "ansible/playbook.yml", "--syntax-check", "-i", "ansible/inventory.ini"],
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
