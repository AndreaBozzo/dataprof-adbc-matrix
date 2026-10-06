"""Connections and per-driver statement options for each backend under test."""

from __future__ import annotations

import os

import adbc_driver_postgresql.dbapi as pg
import adbc_driver_sqlite.dbapi as sq

PG_URI = os.environ.get(
    "DATAPROF_ADBC_PG_URI", "postgresql://postgres:postgres@localhost:54329/postgres"
)

# Statement options that shrink result batches, so that a small result still
# crosses batch boundaries. Values are strings because ADBC options are.
SMALL_BATCH_OPTIONS = {
    "sqlite": {"adbc.sqlite.query.batch_rows": "2"},
    "postgresql": {"adbc.postgresql.batch_size_hint_bytes": "64"},
}


def connect(backend: str):
    if backend == "sqlite":
        return sq.connect()
    if backend == "postgresql":
        return pg.connect(PG_URI)
    raise ValueError(f"unknown backend {backend!r}")


def postgres_available() -> bool:
    try:
        with pg.connect(PG_URI) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchall()
        return True
    except Exception:  # noqa: BLE001 - any failure means unreachable
        return False


def reader(cur, sql: str, options: dict[str, str] | None = None):
    """Execute ``sql`` and return the result as an Arrow ``RecordBatchReader``."""
    if options:
        cur.adbc_statement.set_options(**options)
    cur.execute(sql)
    return cur.fetch_record_batch()
