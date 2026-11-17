# ADBC matrix (dataprof 0.14.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0.  
Packages: dataprof 0.14.0, pyarrow 25.0.1, adbc-driver-manager 1.12.0, adbc-driver-sqlite 1.12.0, adbc-driver-postgresql 1.12.0, duckdb 2.0.0.  
Servers: duckdb v2.0.0, postgresql 170011, sqlite 3.53.3.

Batches: rows per batch the driver emitted, default run / small-batch run. Notes marked (*) are caveats on an `ok` row.

| backend | case | Arrow type | dataprof type | batches | status | detail |
|---|---|---|---|---|---|---|
| duckdb | INTEGER | `int32` | integer | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | BIGINT extremes | `int64` | integer | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | UBIGINT above int64 | `uint64` | integer | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | HUGEINT | `decimal128(38, 0)` | float | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | DECIMAL(18,3) | `decimal128(18, 3)` | float | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | DOUBLE | `double` | float | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | BOOLEAN | `bool` | boolean | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | VARCHAR | `string` | string | 5 / 5 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | VARCHAR as Utf8View | `string_view` | string | 5 / 5 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | VARCHAR as large_string | `large_string` | string | 5 / 5 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | ENUM | `dictionary<values=string, indices=uint8, ordered=0>` | string | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | DATE | `date32[day]` | date | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | TIMESTAMP | `timestamp[us]` | date | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | TIMESTAMPTZ same instant | `timestamp[us, tz=Europe/Rome]` | date | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | TIME | `time64[us]` | string | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | INTERVAL | `month_day_nano_interval` | string | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | UUID | `string` | string | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | UUID lossless | `extension<arrow.uuid>` | string | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | BLOB same length | `binary` | string | 4 / 4 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | INTEGER[] | `list<l: int32>` |  | 3 / ? | profile error | TypeError: Arrow stream column 'v' has unsupported nested type List(Int32, field: 'l'); select flat columns before exporting the stream |
| duckdb | INTEGER[] as ListView | `list_view<l: int32>` |  | 3 / ? | profile error | TypeError: Arrow stream column 'v' has unsupported nested type ListView(Int32, field: 'l'); select flat columns before exporting the stream |
| duckdb | all null | `string` | string | 3 / 3 | ok (*) | (*) small-batch run was not split, so it compares nothing |
| duckdb | empty result | `int32` | integer | 0 / 0 | ok |  |
| postgresql | smallint | `int16` | integer | 5 / 1+1+1+1+1 | ok |  |
| postgresql | integer | `int32` | integer | 3 / 1+1+1 | ok |  |
| postgresql | bigint above 2^53 | `int64` | integer | 3 / 1+1+1 | ok |  |
| postgresql | numeric(12,2) | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 4 / 1+1+1+1 | ok |  |
| postgresql | bigint extremes | `int64` | integer | 4 / 1+1+1+1 | ok |  |
| postgresql | bigint odd above 2^53 | `int64` | integer | 3 / 1+1+1 | ok |  |
| postgresql | numeric(22,2) beyond f64 | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 4 / 1+1+1+1 | mismatch | max 100000000000000000000 vs exact 99999999999999999999.99 (rel 1.0e-22) nearest f64; median 100000000000000000000 vs exact 99999999999999999999.98 (rel 2.0e-22) nearest f64 |
| postgresql | numeric(38,18) fine scale | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 3 / 1+1+1 | ok |  |
| postgresql | double large magnitude | `double` | float | 3 / 1+1+1 | ok |  |
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
| postgresql | uuid | `extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>` | string | 4 / 1+1+1+1 | ok |  |
| postgresql | bytea same length | `binary` | string | 4 / 1+1+1+1 | ok |  |
| postgresql | jsonb | `extension<arrow.json>` | string | 3 / 1+1+1 | ok |  |
| postgresql | integer[] | `list<item: int32>` |  | 3 / ? | profile error | TypeError: Arrow stream column 'v' has unsupported nested type List(Int32); select flat columns before exporting the stream |
| postgresql | all null | `string` | string | 3 / 1+1+1 | ok |  |
| postgresql | empty result | `int32` | integer | 0 / 0 | ok |  |
| sqlite | INTEGER | `int64` | integer | 4 / 2+2 | ok |  |
| sqlite | INTEGER extremes | `int64` | integer | 4 / 2+2 | ok |  |
| sqlite | REAL | `double` | float | 3 / 2+1 | ok |  |
| sqlite | TEXT | `string` | string | 5 / 2+2+1 | ok |  |
| sqlite | TEXT ISO dates | `string` | date | 3 / 2+1 | ok |  |
| sqlite | BLOB same length | `binary` | string | 4 / 2+2 | ok |  |
| sqlite | mixed storage classes | `string` | string | 3 / 2+1 | ok (*) | (*) small batches change patterns, stats (driver output differs) |
| sqlite | all null | `int64` | integer | 3 / 2+1 | ok |  |
| sqlite | empty result | `int64` | integer | 0 / 0 | ok |  |
