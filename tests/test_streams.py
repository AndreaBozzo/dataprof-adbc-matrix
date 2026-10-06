"""Stream behaviour: batch boundaries at scale and errors raised mid-stream.

A profiler must never turn a failed read into a smaller, plausible report.
"""

from __future__ import annotations

import dataprof
import pyarrow as pa
import pytest

from matrix.backends import connect, postgres_available, reader

needs_pg = pytest.mark.skipif(not postgres_available(), reason="docker compose up -d")

ROWS = 200_000
SERIES = f"""
SELECT g AS id,
       CASE WHEN g % 7 = 0 THEN NULL ELSE g * 0.5 END AS amount,
       CASE WHEN g % 11 = 0 THEN NULL ELSE 'k' || (g % 1000) END AS label,
       DATE '2026-01-01' + (g % 365) AS day,
       g % 3 = 0 AS flag
FROM generate_series(1, {ROWS}) g
ORDER BY g
"""


def _profile(sql: str, options: dict | None = None) -> dict:
    with connect("postgresql") as conn, conn.cursor() as cur:
        d = dataprof.profile(reader(cur, sql, options)).to_dict()
    return d


@needs_pg
def test_batch_size_does_not_change_metrics():
    big = _profile(SERIES)
    small = _profile(SERIES, {"adbc.postgresql.batch_size_hint_bytes": "4096"})
    assert big["columns"] == small["columns"]
    assert big["quality"] == small["quality"]
    assert big["columns"][0]["total_count"] == ROWS


@needs_pg
def test_server_error_mid_stream_raises():
    # Division by zero on one late row: the server fails after rows have
    # already been sent, so the reader errors partway through the stream.
    sql = f"""
    SELECT CASE WHEN g = {ROWS - 10} THEN 1 / (g - g) ELSE g END AS v
    FROM generate_series(1, {ROWS}) g
    """
    with pytest.raises(Exception) as info:
        _profile(sql, {"adbc.postgresql.batch_size_hint_bytes": "4096"})
    # 0.12 keeps the driver message as the cause; the top-level text is generic.
    assert "division by zero" in str(info.value.__cause__).lower()


def test_python_reader_error_mid_stream_raises():
    schema = pa.schema([("v", pa.int64())])

    def batches():
        yield pa.record_batch([pa.array([1, 2, 3])], schema=schema)
        raise OSError("connection reset by peer")

    with pytest.raises(Exception) as info:
        dataprof.profile(pa.RecordBatchReader.from_batches(schema, batches()))
    assert "connection reset" in str(info.value.__cause__)
