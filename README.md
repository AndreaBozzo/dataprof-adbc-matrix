# dataprof-adbc-matrix

Can the published [dataprof](https://github.com/AndreaBozzo/dataprof) wheel
profile database query results through [ADBC](https://arrow.apache.org/adbc/),
with no database connector compiled into dataprof?

ADBC drivers return query results as an Arrow `RecordBatchReader`, and
dataprof accepts Arrow streams. This repository measures what survives that
route, per database type, and what does not. Credentials, transactions and
query ownership stay with the caller.

```python
cur.execute("SELECT id, amount, label FROM orders")
report = dataprof.profile(cur.fetch_record_batch())
result = report.check(max_null_percentage={"amount": 25})
```

## Running

```bash
docker compose up -d          # PostgreSQL 17 on localhost:54329
uv sync
uv run python -m matrix.run   # writes results/matrix.md and results/matrix.json
uv run pytest -q              # stream behaviour: batching and mid-stream errors
```

A full `matrix.run` needs every backend: without the container it exits with an
error and writes nothing. `--backend sqlite` runs one backend and only prints, so
a partial run never overwrites `results/`. The tests skip PostgreSQL when it is
missing; set `DATAPROF_ADBC_REQUIRE_PG=1` to make that a failure. Override the
connection with `DATAPROF_ADBC_PG_URI`.

## Method

Each case in [matrix/cases.py](matrix/cases.py) is a column type, a few literal
values, and what an honest profile of those values reports: type, null count,
distinct count, and whether numeric statistics may appear. Expectations follow
dataprof's documented contract where it takes a position (for example, empty
strings and NaN count as null). Each case runs twice, with the driver's default
batching and with tiny batches, and the two column profiles must be identical.
The rows per batch the driver actually emitted are recorded for both runs, and a
small-batch run that was not split is flagged, since it compares nothing. The
results also record the Python, package and server versions they came from.

## Results (dataprof 0.12.0, ADBC 1.x, PostgreSQL 17, SQLite)

See [results/matrix.md](results/matrix.md) for the full table.

Works: integer widths, `bigint` above 2^53 (distinct values stay distinct),
`real`/`double`, `numeric` (arrives as an opaque string extension and is typed
`float`), `boolean`, `text`, `char(n)`, `date`, `timestamp`, `timestamptz`
(two spellings of one instant count as one value), `jsonb` (normalised by the
server), all-null and empty results. Batch size changes no metric over 200,000
rows of mixed types. A server error partway through the stream raises, with the
driver message kept as the exception cause, so a failed read never becomes a
smaller report.

Findings:

| finding | where it belongs |
|---|---|
| `bytea`/`BLOB` distinct count is the number of distinct byte lengths | dataprof#645 |
| PostgreSQL `uuid` arrives as opaque 16-byte binary, so every uuid column reports one distinct value | dataprof#645 |
| `integer[]` and other lists are refused with a clear error | dataprof nested-type work; refusal is honest |
| `''` and NaN count as null, while the database distinguishes them from `NULL` | documented policy; an opt-out would be dataprof#846 |
| `time` and `interval` profile as `string` | no dataprof type for them; counts are right |
| The top-level stream error reads `Arrow stream batch failed (error code 22)`; the useful text is only in `__cause__` | dataprof#876 |
| SQLite driver formats `REAL` values with `%e` while inferring a string column, so `123456789.123` becomes `1.234568e+08`; later batches keep full text | apache/arrow-adbc#4862, repro in [upstream/](upstream/adbc-sqlite-double-to-string/) |

## Not yet measured

- Memory of the whole driver-to-profiler path on a large result.
- Other drivers: DuckDB, Snowflake, BigQuery, Flight SQL.
- Decimal precision beyond what `f64` holds.
