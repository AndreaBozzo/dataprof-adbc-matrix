# Memory of the ADBC path (dataprof 0.12.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0, PostgreSQL via adbc-driver-postgresql 1.12.0. Peak working set over the baseline after connecting, one fresh process per row. Query: five columns from `generate_series`, see [matrix/memory.py](../matrix/memory.py).

| rows | mode | peak over baseline (MiB) | seconds |
|---:|---|---:|---:|
| 1,000,000 | drain | 19.0 | 0.9 |
| 1,000,000 | profile | 64.8 | 2.67 |
| 1,000,000 | table | 84.0 | 3.3 |
| 4,000,000 | drain | 20.4 | 2.8 |
| 4,000,000 | profile | 57.8 | 9.66 |
| 4,000,000 | table | 155.3 | 9.9 |
| 16,000,000 | drain | 20.6 | 8.84 |
| 16,000,000 | profile | 58.0 | 32.88 |
| 16,000,000 | table | 481.3 | 36.54 |
