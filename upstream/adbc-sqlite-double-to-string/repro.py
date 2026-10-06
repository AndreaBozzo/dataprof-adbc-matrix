"""adbc-driver-sqlite: REAL values in a column inferred as string lose precision.

Run: pip install adbc-driver-sqlite pyarrow && python repro.py
"""

import sqlite3

import adbc_driver_sqlite
import adbc_driver_sqlite.dbapi

CASES = {
    "text first": ["'a'", "123456789.123", "3.141592653589793", "0.1"],
    "real first": ["123456789.123", "3.141592653589793", "0.1", "'a'"],
}

print(
    "adbc-driver-sqlite",
    adbc_driver_sqlite.__version__,
    "| sqlite",
    sqlite3.sqlite_version,
)
for name, values in CASES.items():
    rows = ", ".join(f"({i}, {v})" for i, v in enumerate(values))
    setup = ["CREATE TABLE t (id INTEGER, v)", f"INSERT INTO t VALUES {rows}"]
    query = "SELECT v FROM t ORDER BY id"

    ref = sqlite3.connect(":memory:")
    for stmt in setup:
        ref.execute(stmt)
    print(f"\n{name}")
    print(
        "  sqlite3 CAST AS TEXT:",
        [r[0] for r in ref.execute(f"SELECT CAST(v AS TEXT) FROM ({query})")],
    )

    runs = [("default batch", {})]
    if name == "text first":
        # Once the first batch has fixed the type as string, later REALs keep full text.
        runs.append(("batch_rows=1", {"adbc.sqlite.query.batch_rows": "1"}))
    for label, options in runs:
        with adbc_driver_sqlite.dbapi.connect() as conn, conn.cursor() as cur:
            for stmt in setup:
                cur.execute(stmt)
            if options:
                cur.adbc_statement.set_options(**options)
            cur.execute(query)
            table = cur.fetch_arrow_table()
            print(
                f"  ADBC {label:13}:",
                table.schema.field(0).type,
                table.column(0).to_pylist(),
            )
