"""Peak memory of the whole driver-to-profiler path, per result size.

Usage: uv run python -m matrix.memory [--rows 1000000 4000000 16000000]

Each scenario runs in a fresh process and reports its peak working set (peak
RSS on Linux) over the baseline taken after imports and connecting:

- ``drain``: read every batch from the driver and drop it. The driver floor.
- ``profile``: pass the driver's stream to ``dataprof.profile``.
- ``table``: ``fetch_arrow_table`` first. What a materializing caller pays.

Bounded streaming means ``profile`` stays near ``drain`` as rows grow, while
``table`` grows with the result.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
MODES = ("drain", "profile", "table")

# One unique integer, a nullable float, a low-cardinality label, a date and a
# boolean, generated server side so no table has to be loaded first.
QUERY = """
SELECT g AS id,
       CASE WHEN g % 7 = 0 THEN NULL ELSE g * 0.5 END AS amount,
       'k' || (g % 1000) AS label,
       DATE '2026-01-01' + (g % 365) AS day,
       g % 3 = 0 AS flag
FROM generate_series(1, {rows}) g
"""


def _peak_bytes(proc) -> int:
    info = proc.memory_info()
    # Windows reports the peak working set; elsewhere use ru_maxrss.
    if hasattr(info, "peak_wset"):
        return info.peak_wset
    import resource

    scale = 1 if sys.platform == "darwin" else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale


def child(rows: int, mode: str) -> dict:
    import dataprof
    import psutil

    from matrix.backends import connect

    proc = psutil.Process()
    with connect("postgresql") as conn, conn.cursor() as cur:
        before = proc.memory_info().rss
        start = time.perf_counter()
        cur.execute(QUERY.format(rows=rows))
        batches = 0
        if mode == "drain":
            for _ in cur.fetch_record_batch():
                batches += 1
        elif mode == "profile":
            report = dataprof.profile(cur.fetch_record_batch())
            assert report.to_dict()["columns"][0]["total_count"] == rows
        else:
            table = cur.fetch_arrow_table()
            batches = len(table.to_batches())
            report = dataprof.profile(table)
            assert report.to_dict()["columns"][0]["total_count"] == rows
        elapsed = time.perf_counter() - start
    return {
        "rows": rows,
        "mode": mode,
        "batches": batches or None,
        "baseline_mib": round(before / 2**20, 1),
        "peak_over_baseline_mib": round((_peak_bytes(proc) - before) / 2**20, 1),
        "seconds": round(elapsed, 2),
    }


def _environment() -> dict:
    import platform
    from importlib.metadata import version

    from matrix.run import PACKAGES

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {p: version(p) for p in PACKAGES},
    }


def _markdown(env: dict, results: list[dict]) -> str:
    out = [
        f"# Memory of the ADBC path (dataprof {env['packages']['dataprof']})",
        "",
        (
            f"Python {env['python']} on {env['platform']}, PostgreSQL via "
            f"adbc-driver-postgresql {env['packages']['adbc-driver-postgresql']}. "
            "Peak working set over the baseline after connecting, one fresh "
            "process per row. Query: five columns from `generate_series`, see "
            "[matrix/memory.py](../matrix/memory.py)."
        ),
        "",
        "| rows | mode | peak over baseline (MiB) | seconds |",
        "|---:|---|---:|---:|",
    ]
    for r in results:
        out.append(
            f"| {r['rows']:,} | {r['mode']} | {r['peak_over_baseline_mib']} "
            f"| {r['seconds']} |"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--rows", type=int, nargs="+", default=[1_000_000, 4_000_000, 16_000_000]
    )
    ap.add_argument("--child", nargs=2, metavar=("ROWS", "MODE"))
    args = ap.parse_args()
    if args.child:
        print(json.dumps(child(int(args.child[0]), args.child[1])))
        return

    from matrix.backends import postgres_available

    if not postgres_available():
        sys.exit("postgresql unreachable (docker compose up -d); nothing written")
    results = []
    for rows in args.rows:
        for mode in MODES:
            out = subprocess.run(
                [sys.executable, "-m", "matrix.memory", "--child", str(rows), mode],
                capture_output=True,
                text=True,
                check=True,
            )
            r = json.loads(out.stdout.strip().splitlines()[-1])
            print(r, flush=True)
            results.append(r)
    env = _environment()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "memory.json").write_text(
        json.dumps({"environment": env, "results": results}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (RESULTS / "memory.md").write_text(
        _markdown(env, results), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
