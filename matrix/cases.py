"""Type cases: a column type, literal values, and what an honest profile says.

Expectations describe the logical data, not what dataprof happens to return.
A mismatch is a finding: either a dataprof gap or an expectation to revisit.

Expectation keys:
- ``data_type``: accepted dataprof type names (any of).
- ``null_count``, ``unique_count``, ``total_count``: exact.
- ``min``, ``max``: exact numeric stats.
- ``numeric_stats``: True if mean/min/max must be present, False if they
  must be absent (opaque or non-numeric values must not get numeric stats).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    name: str
    sql_type: str
    values: list[str]  # SQL literals, one per row
    expect: dict = field(default_factory=dict)
    note: str = ""
    # The driver itself returns different values under different batching,
    # so the small-batch comparison is reported but not counted as a mismatch.
    driver_batch_variant: bool = False


POSTGRES: list[Case] = [
    Case(
        "smallint",
        "smallint",
        ["1", "2", "2", "NULL", "-32768"],
        {
            "data_type": ["integer"],
            "null_count": 1,
            "unique_count": 3,
            "min": -32768.0,
            "max": 2.0,
        },
    ),
    Case(
        "integer",
        "integer",
        ["10", "20", "NULL"],
        {
            "data_type": ["integer"],
            "null_count": 1,
            "unique_count": 2,
            "min": 10.0,
            "max": 20.0,
        },
    ),
    Case(
        "bigint above 2^53",
        "bigint",
        ["9007199254740993", "9007199254740992", "NULL"],
        {"data_type": ["integer"], "null_count": 1, "unique_count": 2},
        "Two values that collapse to one if converted through f64.",
    ),
    Case(
        "numeric(12,2)",
        "numeric(12,2)",
        ["1.10", "2.25", "NULL", "2.25"],
        {
            "data_type": ["float"],
            "null_count": 1,
            "unique_count": 2,
            "min": 1.1,
            "max": 2.25,
        },
        "The PostgreSQL driver returns NUMERIC as a string column.",
    ),
    Case(
        "real",
        "real",
        ["1.5", "2.5", "NULL"],
        {
            "data_type": ["float"],
            "null_count": 1,
            "unique_count": 2,
            "min": 1.5,
            "max": 2.5,
        },
    ),
    Case(
        "double with NaN/Infinity",
        "double precision",
        ["1.0", "'NaN'", "'Infinity'", "NULL"],
        {"data_type": ["float"], "null_count": 2, "unique_count": 2},
        "dataprof counts NaN as null (documented null_tokens policy).",
    ),
    Case(
        "boolean",
        "boolean",
        ["true", "false", "true", "NULL"],
        {
            "data_type": ["boolean"],
            "null_count": 1,
            "unique_count": 2,
            "numeric_stats": False,
        },
    ),
    Case(
        "text",
        "text",
        ["'a'", "'è'", "''", "NULL", "'a'"],
        {"data_type": ["string"], "null_count": 2, "unique_count": 2},
        "The database keeps '' apart from NULL; dataprof counts it as null "
        "(documented null_tokens policy, opt-out would be dataprof#846).",
    ),
    Case(
        "char(3)",
        "char(3)",
        ["'ab'", "'abc'", "NULL"],
        {"data_type": ["string"], "null_count": 1, "unique_count": 2},
    ),
    Case(
        "date",
        "date",
        ["'2026-01-01'", "'2026-01-02'", "NULL"],
        {
            "data_type": ["date"],
            "null_count": 1,
            "unique_count": 2,
            "numeric_stats": False,
        },
    ),
    Case(
        "timestamp",
        "timestamp",
        ["'2026-01-01 10:00:00'", "'2026-01-01 11:00:00'", "NULL"],
        {
            "data_type": ["date"],
            "null_count": 1,
            "unique_count": 2,
            "numeric_stats": False,
        },
    ),
    Case(
        "timestamptz same instant",
        "timestamptz",
        ["'2026-01-01 10:00:00+00'", "'2026-01-01 12:00:00+02'", "NULL"],
        {
            "data_type": ["date"],
            "null_count": 1,
            "unique_count": 1,
            "numeric_stats": False,
        },
        "Both literals are the same instant.",
    ),
    Case(
        "time",
        "time",
        ["'10:00:00'", "'11:30:00'", "NULL"],
        {"null_count": 1, "unique_count": 2},
    ),
    Case(
        "interval",
        "interval",
        ["'1 day'", "'2 hours'", "NULL"],
        {"null_count": 1, "unique_count": 2},
    ),
    Case(
        "uuid",
        "uuid",
        [
            "'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'",
            "'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12'",
            "'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'",
            "NULL",
        ],
        {"null_count": 1, "unique_count": 2, "numeric_stats": False},
    ),
    Case(
        "bytea same length",
        "bytea",
        ["'\\x00'", "'\\x01'", "'\\x0203'", "NULL"],
        {"null_count": 1, "unique_count": 3, "numeric_stats": False},
        "Two distinct one-byte values. Tracked in dataprof#645.",
    ),
    Case(
        "jsonb",
        "jsonb",
        ["'{\"a\":1}'", "'{\"a\": 1}'", "NULL"],
        {"null_count": 1, "unique_count": 1},
        "jsonb normalises both literals to the same value.",
    ),
    Case(
        "integer[]",
        "integer[]",
        ["'{1,2}'", "'{3}'", "NULL"],
        {"null_count": 1, "unique_count": 2, "numeric_stats": False},
    ),
    Case(
        "all null",
        "text",
        ["NULL", "NULL", "NULL"],
        {"null_count": 3, "total_count": 3},
    ),
    Case(
        "empty result",
        "integer",
        [],
        {"total_count": 0, "null_count": 0},
    ),
]

SQLITE: list[Case] = [
    Case(
        "INTEGER",
        "INTEGER",
        ["1", "2", "NULL", "2"],
        {
            "data_type": ["integer"],
            "null_count": 1,
            "unique_count": 2,
            "min": 1.0,
            "max": 2.0,
        },
    ),
    Case(
        "REAL",
        "REAL",
        ["1.5", "2.5", "NULL"],
        {
            "data_type": ["float"],
            "null_count": 1,
            "unique_count": 2,
            "min": 1.5,
            "max": 2.5,
        },
    ),
    Case(
        "TEXT",
        "TEXT",
        ["'a'", "'è'", "''", "NULL", "'a'"],
        {"data_type": ["string"], "null_count": 2, "unique_count": 2},
        "Empty string counted as null, as for PostgreSQL text.",
    ),
    Case(
        "TEXT ISO dates",
        "TEXT",
        ["'2026-01-01'", "'2026-01-02'", "NULL"],
        {"data_type": ["date"], "null_count": 1, "unique_count": 2},
    ),
    Case(
        "BLOB same length",
        "BLOB",
        ["x'00'", "x'01'", "x'0203'", "NULL"],
        {"null_count": 1, "unique_count": 3, "numeric_stats": False},
        "Two distinct one-byte values. Tracked in dataprof#645.",
    ),
    Case(
        "mixed storage classes",
        "",
        ["1", "'a'", "2.5"],
        {"null_count": 0, "unique_count": 3},
        "SQLite is dynamically typed. The driver renders 2.5 as 2.500000e+00 "
        "when it shares a batch with text, so batching changes the strings.",
        driver_batch_variant=True,
    ),
    Case(
        "all null",
        "TEXT",
        ["NULL", "NULL", "NULL"],
        {"null_count": 3, "total_count": 3},
    ),
    Case(
        "empty result",
        "INTEGER",
        [],
        {"total_count": 0, "null_count": 0},
    ),
]

CASES = {"postgresql": POSTGRES, "sqlite": SQLITE}
