Title: c/driver/sqlite: REAL values lose precision when a column is inferred as string

### What happened?

In a column holding both REAL and TEXT values, the SQLite driver widens the inferred type to string. REAL values converted during that inference are formatted with `snprintf("%e")`, which keeps six significant digits:

- `123456789.123` becomes `1.234568e+08`
- `3.141592653589793` becomes `3.141593e+00`

After the first batch has fixed the type as string, REAL values in later batches keep their full text (`123456789.123`). The same query therefore returns different values depending on `adbc.sqlite.query.batch_rows`, and with the default batch size it returns rounded values for any small result.

Expected: the same text SQLite produces for `CAST(v AS TEXT)`, or at least a round-trip representation, regardless of batching.

Both paths that convert a double to string go through `InternalSqliteStatementReaderAppendDoubleToBinary`: a REAL arriving after the column is already string ([L1108](https://github.com/apache/arrow-adbc/blob/ba7e7f540da64555507ad14eeebd373f0ff5d9a8/c/driver/sqlite/statement_reader.c#L1108)), and buffered doubles upcast when TEXT arrives ([L1021](https://github.com/apache/arrow-adbc/blob/ba7e7f540da64555507ad14eeebd373f0ff5d9a8/c/driver/sqlite/statement_reader.c#L1021)). The format is at [L961](https://github.com/apache/arrow-adbc/blob/ba7e7f540da64555507ad14eeebd373f0ff5d9a8/c/driver/sqlite/statement_reader.c#L961).

A possible fix is `%.17g`, which round-trips every double. Matching SQLite's own text exactly would need its formatter (for example `sqlite3_column_text` where the statement is still positioned on the row).

### How can we reproduce the bug?

```python
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
```

Output:

```
adbc-driver-sqlite 1.12.0 | sqlite 3.53.1

text first
  sqlite3 CAST AS TEXT: ['a', '123456789.123', '3.1415926535897931', '0.1']
  ADBC default batch: string ['a', '1.234568e+08', '3.141593e+00', '1.000000e-01']
  ADBC batch_rows=1 : string ['a', '123456789.123', '3.1415926535897931', '0.1']

real first
  sqlite3 CAST AS TEXT: ['123456789.123', '3.1415926535897931', '0.1', 'a']
  ADBC default batch: string ['1.234568e+08', '3.141593e+00', '1.000000e-01', 'a']
```

### Environment/Setup

adbc-driver-sqlite 1.12.0 (pip), pyarrow, SQLite 3.53.1, Python 3.14, Windows 11. The formatting code is unchanged on `main` at ba7e7f5.

Found while building a type matrix for ADBC results: https://github.com/AndreaBozzo/dataprof-adbc-matrix (repro in `upstream/adbc-sqlite-double-to-string/`).
