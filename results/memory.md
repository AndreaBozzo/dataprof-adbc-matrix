# Memory of the ADBC path (dataprof 0.14.0)

Python 3.14.6 on Windows-11-10.0.26300-SP0, PostgreSQL via adbc-driver-postgresql 1.12.0. Peak working set over the baseline after connecting, one fresh process per row. Query: five columns from `generate_series`, see [matrix/memory.py](../matrix/memory.py).

| rows | mode | peak over baseline (MiB) | seconds |
|---:|---|---:|---:|
| 1,000,000 | drain | 19.1 | 0.75 |
| 1,000,000 | profile | 64.7 | 3.42 |
| 1,000,000 | table | 84.1 | 3.53 |
| 4,000,000 | drain | 19.9 | 2.98 |
| 4,000,000 | profile | 57.9 | 11.06 |
| 4,000,000 | table | 155.5 | 12.81 |
| 16,000,000 | drain | 20.7 | 10.23 |
| 16,000,000 | profile | 58.2 | 34.35 |
| 16,000,000 | table | 480.8 | 33.46 |
