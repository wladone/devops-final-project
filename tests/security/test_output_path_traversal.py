"""Guard against ``--output-dir`` values that escape the repo or
land in privileged locations.

The current contract is "we honour whatever path the caller gives us"
(per ``cli.py`` + ``write_reports``), so this test asserts the *observed*
behaviour rather than a hard rejection: the directory is created relative
to whatever absolute path is resolved, and the three artefacts only ever
appear inside that directory — never outside it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_quality_monitor.pipeline import run_pipeline

pytestmark = pytest.mark.security

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "rings_control.csv"
RULES = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "sparrowhawk_rules.yml"


def test_traversal_segments_are_resolved_inside_tmpdir(tmp_path: Path) -> None:
    """A relative path with ``..`` segments must resolve into a directory
    that *we asked for*, not escape into a sibling tree."""
    traversal_target = tmp_path / "a" / ".." / "reports"
    outcome = run_pipeline(input_path=FIXTURE, rules_path=RULES, output_dir=traversal_target)

    resolved = traversal_target.resolve()
    # Every artefact must live inside the resolved target dir.
    for kind, path in outcome.output_files.items():
        assert Path(path).resolve().is_relative_to(resolved), (
            f"{kind} artefact {path} escaped {resolved}"
        )
    # And nothing should have been written outside tmp_path overall.
    for path in outcome.output_files.values():
        assert Path(path).resolve().is_relative_to(tmp_path.resolve()), (
            f"Artefact {path} escaped the test's tmp tree"
        )


def test_absolute_output_dir_is_created(tmp_path: Path) -> None:
    deep = tmp_path / "nested" / "deeper" / "reports"
    outcome = run_pipeline(input_path=FIXTURE, rules_path=RULES, output_dir=deep)
    assert deep.is_dir()
    for path in outcome.output_files.values():
        assert path.exists()
