# Memory of the ADBC path (dataprof 0.13.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0, PostgreSQL via adbc-driver-postgresql 1.12.0. Peak working set over the baseline after connecting, one fresh process per row. Query: five columns from `generate_series`, see [matrix/memory.py](../matrix/memory.py).

| rows | mode | peak over baseline (MiB) | seconds |
|---:|---|---:|---:|
| 1,000,000 | drain | 19.3 | 0.92 |
| 1,000,000 | profile | 64.4 | 2.3 |
| 1,000,000 | table | 84.2 | 2.86 |
| 4,000,000 | drain | 20.3 | 3.04 |
| 4,000,000 | profile | 58.1 | 7.08 |
| 4,000,000 | table | 156.1 | 7.67 |
| 16,000,000 | drain | 20.6 | 9.16 |
| 16,000,000 | profile | 58.0 | 24.91 |
| 16,000,000 | table | 481.2 | 29.06 |
