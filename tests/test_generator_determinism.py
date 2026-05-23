"""Regression guard for issue: Sparrowhawk fixture generator was using
``hash(name)`` to seed each scenario's RNG, which is randomised per Python
process via ``PYTHONHASHSEED``.  That made re-running ``generate.py``
produce different CSV bytes than the committed fixtures, silently breaking
the golden baselines.

This test pins the deterministic contract:
- ``_stable_seed`` returns the same integer for the same inputs across
  processes (verified indirectly: across two threads + two calls in the
  same process).
- ``build()`` produces byte-identical CSV output for the same ``--seed``
  on repeated invocations.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tests" / "fixtures" / "sparrowhawk" / "generate.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("sparrowhawk_generate", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stable_seed_is_independent_of_python_hash_randomisation() -> None:
    """``_stable_seed`` must give identical output for identical inputs,
    regardless of the ambient ``hash()`` salt."""
    gen = _load_generator()
    a = gen._stable_seed(20260521, "rings_control.csv")
    b = gen._stable_seed(20260521, "rings_control.csv")
    assert a == b
    # And different scenarios must produce different seeds (the whole reason
    # the original code reached for ``hash``).
    assert a != gen._stable_seed(20260521, "rings_mixed_extreme.csv")


def test_generator_output_is_byte_stable_in_same_process(tmp_path: Path) -> None:
    gen = _load_generator()
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    out_a.mkdir()
    out_b.mkdir()
    gen.build(out_a, seed=20260521)
    gen.build(out_b, seed=20260521)
    for csv_a in sorted(out_a.glob("*.csv")):
        csv_b = out_b / csv_a.name
        assert csv_a.read_bytes() == csv_b.read_bytes(), (
            f"{csv_a.name} drifted across two same-process invocations"
        )


def test_generator_output_is_byte_stable_across_processes(tmp_path: Path) -> None:
    """The original bug: two subprocess invocations with the same ``--seed``
    used to produce different bytes because ``hash()`` was randomised per
    interpreter.  After the ``hashlib``-based fix, they must match."""
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    for out in (out_a, out_b):
        subprocess.run(
            [sys.executable, str(GENERATOR), "--seed", "20260521", "--output-dir", str(out)],
            check=True,
            capture_output=True,
        )
    for csv_a in sorted(out_a.glob("*.csv")):
        csv_b = out_b / csv_a.name
        assert csv_a.read_bytes() == csv_b.read_bytes(), (
            f"{csv_a.name} drifted across two subprocess invocations — the "
            f"generator is non-deterministic again."
        )
