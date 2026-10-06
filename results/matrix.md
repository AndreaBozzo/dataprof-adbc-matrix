# ADBC matrix (dataprof 0.12.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0.  
Packages: dataprof 0.12.0, pyarrow 25.0.1, adbc-driver-manager 1.12.0, adbc-driver-sqlite 1.12.0, adbc-driver-postgresql 1.12.0.  
Servers: postgresql 170011, sqlite 3.53.3.

Batches: rows per batch the driver emitted, default run / small-batch run. Notes marked (*) are caveats on an `ok` row.

| backend | case | Arrow type | dataprof type | batches | status | detail |
|---|---|---|---|---|---|---|
| postgresql | smallint | `int16` | integer | 5 / 1+1+1+1+1 | ok |  |
| postgresql | integer | `int32` | integer | 3 / 1+1+1 | ok |  |
| postgresql | bigint above 2^53 | `int64` | integer | 3 / 1+1+1 | mismatch | max 9007199254740992 vs exact 9007199254740993 (rel 1.1e-16) nearest f64; mean 9007199254740992 vs exact 9007199254740992.5 (rel 5.6e-17) nearest f64; median 9007199254740992 vs exact 9007199254740992.5 (rel 5.6e-17) nearest f64; variance 0 vs exact 0.5 (rel 1.0e+00); std_dev 0 vs exact 0.7071 (rel 1.0e+00) |
| postgresql | numeric(12,2) | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 4 / 1+1+1+1 | ok |  |
| postgresql | bigint extremes | `int64` | integer | 4 / 1+1+1+1 | mismatch | max 9223372036854775808 vs exact 9223372036854775807 (rel 1.1e-19) nearest f64; mean 3074457345618258432 vs exact 3074457345618258601.6667 (rel 5.5e-17) nearest f64; median 9223372036854775808 vs exact 9223372036854775806 (rel 2.2e-19) nearest f64; variance 113427455640312833747435490100000000000 vs exact 113427455640312821136011458400000000000 (rel 1.1e-16); std_dev 10650232656628344832 vs exact 10650232656628343400.1827 (rel 1.3e-16) |
| postgresql | bigint odd above 2^53 | `int64` | integer | 3 / 1+1+1 | mismatch | min 9007199254740992 vs exact 9007199254740993 (rel 1.1e-16) nearest f64; max 9007199254740996 vs exact 9007199254740997 (rel 1.1e-16) nearest f64; mean 9007199254740994 vs exact 9007199254740995 (rel 1.1e-16); median 9007199254740996 vs exact 9007199254740995 (rel 1.1e-16) nearest f64; variance 5.3333 vs exact 4 (rel 3.3e-01); std_dev 2.3094 vs exact 2 (rel 1.5e-01) |
| postgresql | numeric(22,2) beyond f64 | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | 4 / 1+1+1+1 | mismatch | max 100000000000000000000 vs exact 99999999999999999999.99 (rel 1.0e-22) nearest f64; mean 66666666666666663936 vs exact 66666666666666666666.66 (rel 4.1e-17) nearest f64; median 100000000000000000000 vs exact 99999999999999999999.98 (rel 2.0e-22) nearest f64; variance 3333333333333333636082979411000000000000 vs exact 3333333333333333333331666667000000000000 (rel 9.1e-17); std_dev 57735026918962577408 vs exact 57735026918962576450.9004 (rel 1.7e-17) nearest f64 |
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
| postgresql | uuid | `extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>` | string | 4 / 1+1+1+1 | mismatch | unique_count 1 != 2 |
| postgresql | bytea same length | `binary` | string | 4 / 1+1+1+1 | mismatch | unique_count 2 != 3 |
| postgresql | jsonb | `extension<arrow.json>` | string | 3 / 1+1+1 | ok |  |
| postgresql | integer[] | `list<item: int32>` |  | 3 / ? | profile error | TypeError: Arrow stream column 'v' has unsupported nested type List(Int32); select flat columns before exporting the stream |
| postgresql | all null | `string` | string | 3 / 1+1+1 | ok |  |
| postgresql | empty result | `int32` | integer | 0 / 0 | ok |  |
| sqlite | INTEGER | `int64` | integer | 4 / 2+2 | ok |  |
| sqlite | INTEGER extremes | `int64` | integer | 4 / 2+2 | mismatch | max 9223372036854775808 vs exact 9223372036854775807 (rel 1.1e-19) nearest f64; mean 3074457345618258432 vs exact 3074457345618258601.6667 (rel 5.5e-17) nearest f64; median 9223372036854775808 vs exact 9223372036854775806 (rel 2.2e-19) nearest f64; variance 113427455640312833747435490100000000000 vs exact 113427455640312821136011458400000000000 (rel 1.1e-16); std_dev 10650232656628344832 vs exact 10650232656628343400.1827 (rel 1.3e-16) |
| sqlite | REAL | `double` | float | 3 / 2+1 | ok |  |
| sqlite | TEXT | `string` | string | 5 / 2+2+1 | ok |  |
| sqlite | TEXT ISO dates | `string` | date | 3 / 2+1 | ok |  |
| sqlite | BLOB same length | `binary` | string | 4 / 2+2 | mismatch | unique_count 2 != 3 |
| sqlite | mixed storage classes | `string` | string | 3 / 2+1 | ok (*) | (*) small batches change patterns, stats (driver output differs) |
| sqlite | all null | `int64` | integer | 3 / 2+1 | ok |  |
| sqlite | empty result | `int64` | integer | 0 / 0 | ok |  |
