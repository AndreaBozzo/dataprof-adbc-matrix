# ADBC matrix (dataprof 0.12.0)

| backend | case | Arrow type | dataprof type | status | detail |
|---|---|---|---|---|---|
| postgresql | smallint | `int16` | integer | ok |  |
| postgresql | integer | `int32` | integer | ok |  |
| postgresql | bigint above 2^53 | `int64` | integer | ok |  |
| postgresql | numeric(12,2) | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | float | ok |  |
| postgresql | real | `float` | float | ok |  |
| postgresql | double with NaN/Infinity | `double` | float | ok |  |
| postgresql | boolean | `bool` | boolean | ok |  |
| postgresql | text | `string` | string | ok |  |
| postgresql | char(3) | `string` | string | ok |  |
| postgresql | date | `date32[day]` | date | ok |  |
| postgresql | timestamp | `timestamp[us]` | date | ok |  |
| postgresql | timestamptz same instant | `timestamp[us, tz=UTC]` | date | ok |  |
| postgresql | time | `time64[us]` | string | ok |  |
| postgresql | interval | `month_day_nano_interval` | string | ok |  |
| postgresql | uuid | `extension<arrow.opaque[storage_type=binary, type_name=uuid, vendor_name=PostgreSQL]>` | string | mismatch | unique_count 1 != 2 |
| postgresql | bytea same length | `binary` | string | mismatch | unique_count 2 != 3 |
| postgresql | jsonb | `extension<arrow.json>` | string | ok |  |
| postgresql | integer[] | `list<item: int32>` |  | profile error | TypeError: Arrow stream column 'v' has unsupported nested type List(Int32); select flat columns before exporting the stream |
| postgresql | all null | `string` | string | ok |  |
| postgresql | empty result | `int32` | integer | ok |  |
| sqlite | INTEGER | `int64` | integer | ok |  |
| sqlite | REAL | `double` | float | ok |  |
| sqlite | TEXT | `string` | string | ok |  |
| sqlite | TEXT ISO dates | `string` | date | ok |  |
| sqlite | BLOB same length | `binary` | string | mismatch | unique_count 2 != 3 |
| sqlite | mixed storage classes | `string` | string | ok |  |
| sqlite | all null | `int64` | integer | ok |  |
| sqlite | empty result | `int64` | integer | ok |  |
