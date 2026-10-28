# Memory of the ADBC path (dataprof 0.13.1)

Python 3.14.6 on Windows-11-10.0.26300-SP0, PostgreSQL via adbc-driver-postgresql 1.12.0. Peak working set over the baseline after connecting, one fresh process per row. Query: five columns from `generate_series`, see [matrix/memory.py](../matrix/memory.py).

| rows | mode | peak over baseline (MiB) | seconds |
|---:|---|---:|---:|
| 1,000,000 | drain | 19.1 | 0.46 |
| 1,000,000 | profile | 64.8 | 1.17 |
| 1,000,000 | table | 83.9 | 1.2 |
| 4,000,000 | drain | 20.4 | 1.66 |
| 4,000,000 | profile | 58.0 | 3.96 |
| 4,000,000 | table | 155.8 | 5.1 |
| 16,000,000 | drain | 20.5 | 5.86 |
| 16,000,000 | profile | 58.1 | 16.31 |
| 16,000,000 | table | 481.4 | 21.48 |
