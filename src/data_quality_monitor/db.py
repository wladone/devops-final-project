"""Database engine + session management for the SQL-backed pipeline.

Defaults to SQLite at `data/db/dq.db` so the demo runs end-to-end with zero
external infrastructure. The same code path drives Postgres by setting
`DQ_DATABASE_URL=postgresql+psycopg2://user:pass@host/db` — useful when the
demo runs against the docker-compose stack.

Why one file with table prefixes (psq_*, ricos_*, analytics_*) instead of real
SQL schemas: SQLite's schema support requires `ATTACH DATABASE` gymnastics
that don't translate cleanly to Postgres. Table prefixes give the same
logical grouping ("which tables belong to which source") and work identically
on both engines. Swapping to real schemas later is a one-line change per
model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


DEFAULT_SQLITE_PATH = Path("data/db/dq.db")


def resolve_database_url(override: str | None = None) -> str:
    if override:
        return override
    if env := os.environ.get("DQ_DATABASE_URL"):
        return env
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def make_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    return create_engine(resolve_database_url(url), echo=echo, future=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def session_scope(engine: Engine) -> Iterator[Session]:
    """Context-managed session that commits on exit, rolls back on error."""
    factory = make_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
