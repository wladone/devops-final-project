"""Enable coverage.py to track subprocesses launched during tests.

When ``COVERAGE_PROCESS_START`` is set, ``coverage.process_startup`` hooks
into any Python interpreter that imports ``sitecustomize`` — including the
ones spawned by ``subprocess.run`` in the CLI contract tests — so cli.py
and __main__.py are properly traced.

In normal (non-CI) runs the env var is unset and this file is a no-op.
"""

import os

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage

        coverage.process_startup()
    except ImportError:
        pass
