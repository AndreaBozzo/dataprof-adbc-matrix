# ADBC matrix (dataprof 0.12.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0.  
Packages: dataprof 0.12.0, pyarrow 25.0.1, adbc-driver-manager 1.12.0, adbc-driver-sqlite 1.12.0, adbc-driver-postgresql 1.12.0.  
Servers: postgresql 170011, sqlite 3.53.3.

Batches: rows per batch the driver emitted, default run / small-batch run. Notes marked (*) are caveats on an `ok` row.

| backend | case | Arrow type | dataprof type | batches | status | detail |
|---|---|---|---|---|---|---|
| postgresql | smallint | `int16` | integer | 5 / 1+1+1+1+1 | ok |  |
| postgresql | integer | `int32` | integer | 3 / 1+1+1 | ok |  |
| postgresql | bigint above 2^53 | `int64` | integer | 3 / 1+1+1 | ok |  |
| postgresql | numeric(12,2) | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 4 / 1+1+1+1 | ok |  |
| postgresql | real | `float` | float | 3 / 1+1+1 | ok |  |
| postgresql | double with NaN/Infinity | `double` | float | 4 / 1+1+1+1 | ok |  |
| postgresql | boolean | `bool` | boolean | 4 / 1+1+1+1 | ok |  |
| postgresql | text | `string` | string | 5 / 1+1+1+1+1 | ok |  |
| postgresql | char(3) | `string` | string | 3 / 1+1+1 | ok |  |
| postgresql | date | `date32[day]` | date | 3 / 1+1+1 | ok |  |
| postgresql | timestamp | `timestamp[us]` | date | 3 / 1+1+1 | ok |  |
| postgresql | timestamptz same instant | `timestamp[us, tz=UTC]` | date | 3 / 1+1+1 | ok |  |
| postgresql | time | `time64[us]` | string | 3 / 1+1+1 | ok |  |
| postgresql | interval | `month_day_nano_interval` | string | 3 / 1+1+1 | ok |  |
| postgresql | uuid | `extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>` | string | 4 / 1+1+1+1 | mismatch | unique_count 1 != 2 |
| postgresql | bytea same length | `binary` | string | 4 / 1+1+1+1 | mismatch | unique_count 2 != 3 |
| postgresql | jsonb | `extension<arrow.json>` | string | 3 / 1+1+1 | ok |  |
| postgresql | integer[] | `list<item: int32>` |  | 3 / ? | profile error | TypeError: Arrow stream column 'v' has unsupported nested type List(Int32); select flat columns before exporting the stream |
| postgresql | all null | `string` | string | 3 / 1+1+1 | ok |  |
| postgresql | empty result | `int32` | integer | 0 / 0 | ok |  |
| sqlite | INTEGER | `int64` | integer | 4 / 2+2 | ok |  |
| sqlite | REAL | `double` | float | 3 / 2+1 | ok |  |
| sqlite | TEXT | `string` | string | 5 / 2+2+1 | ok |  |
| sqlite | TEXT ISO dates | `string` | date | 3 / 2+1 | ok |  |
| sqlite | BLOB same length | `binary` | string | 4 / 2+2 | mismatch | unique_count 2 != 3 |
| sqlite | mixed storage classes | `string` | string | 3 / 2+1 | ok (*) | (*) small batches change patterns, stats (driver output differs) |
| sqlite | all null | `int64` | integer | 3 / 2+1 | ok |  |
| sqlite | empty result | `int64` | integer | 0 / 0 | ok |  |
