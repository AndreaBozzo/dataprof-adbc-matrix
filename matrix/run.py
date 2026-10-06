"""Run every type case through ADBC into dataprof and write the matrix.

Usage: uv run python -m matrix.run [--backend sqlite|postgresql]

Each case runs twice, once with the driver's default batching and once with
tiny batches, and the two serialized column profiles must be identical.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import dataprof

from matrix.backends import SMALL_BATCH_OPTIONS, connect, postgres_available, reader
from matrix.cases import CASES, Case

RESULTS = Path(__file__).resolve().parent.parent / "results"


def _table_sql(backend: str, case: Case) -> list[str]:
    col = f"v {case.sql_type}".strip()
    stmts = ["DROP TABLE IF EXISTS t", f"CREATE TABLE t (id integer, {col})"]
    if case.values:
        rows = ", ".join(f"({i}, {v})" for i, v in enumerate(case.values))
        stmts.append(f"INSERT INTO t VALUES {rows}")
    return stmts


def _profile_column(backend: str, case: Case, options: dict | None):
    with connect(backend) as conn:
        with conn.cursor() as cur:
            for stmt in _table_sql(backend, case):
                cur.execute(stmt)
            conn.commit()
        with conn.cursor() as cur:
            rbr = reader(cur, "SELECT v FROM t ORDER BY id", options)
            arrow_type = str(rbr.schema.field(0).type)
            try:
                report = dataprof.profile(rbr)
            except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                return arrow_type, None, f"{type(exc).__name__}: {exc}"
    return arrow_type, report.to_dict()["columns"][0], None


def _check(expect: dict, col: dict) -> list[str]:
    problems = []
    stats = col.get("stats") or {}
    for key, want in expect.items():
        if key == "data_type":
            if col.get("data_type") not in want:
                problems.append(f"data_type {col.get('data_type')} not in {want}")
        elif key in ("min", "max"):
            if stats.get(key) != want:
                problems.append(f"{key} {stats.get(key)} != {want}")
        elif key == "numeric_stats":
            has = "mean" in stats
            if has != want:
                problems.append(f"numeric stats {'present' if has else 'absent'}")
        elif col.get(key) != want:
            problems.append(f"{key} {col.get(key)} != {want}")
    return problems


def run_case(backend: str, case: Case) -> dict:
    row = {
        "backend": backend,
        "case": case.name,
        "sql_type": case.sql_type,
        "note": case.note,
    }
    try:
        arrow_type, col, err = _profile_column(backend, case, None)
    except Exception as exc:  # noqa: BLE001 - recorded in the matrix
        row.update(status="driver error", detail=f"{type(exc).__name__}: {exc}")
        return row
    row["arrow_type"] = arrow_type
    if err:
        row.update(status="profile error", detail=err)
        return row
    row["observed"] = {
        k: col.get(k)
        for k in ("data_type", "total_count", "null_count", "unique_count")
    }
    row["observed"]["stats"] = col.get("stats")
    problems = _check(case.expect, col)

    try:
        _, small, small_err = _profile_column(
            backend, case, SMALL_BATCH_OPTIONS[backend]
        )
    except Exception as exc:  # noqa: BLE001 - recorded in the matrix
        small, small_err = None, f"{type(exc).__name__}: {exc}"
    if small_err:
        problems.append(f"small batches: {small_err}")
    elif small != col:
        diff = sorted(k for k in set(col) | set(small) if col.get(k) != small.get(k))
        msg = f"small batches change {', '.join(diff)}"
        if case.driver_batch_variant:
            row["batch_note"] = msg + " (driver output differs)"
        else:
            problems.append(msg)

    row.update(status="ok" if not problems else "mismatch", detail="; ".join(problems))
    return row


def _markdown(rows: list[dict]) -> str:
    out = [
        f"# ADBC matrix (dataprof {dataprof.__version__})",
        "",
        "| backend | case | Arrow type | dataprof type | status | detail |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        dtype = (r.get("observed") or {}).get("data_type", "")
        detail = (r.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        out.append(
            f"| {r['backend']} | {r['case']} | `{r.get('arrow_type', '')}` "
            f"| {dtype} | {r['status']} | {detail} |"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=sorted(CASES))
    args = ap.parse_args()
    backends = [args.backend] if args.backend else sorted(CASES)
    rows = []
    for backend in backends:
        if backend == "postgresql" and not postgres_available():
            print("postgresql unreachable, skipped (docker compose up -d)")
            continue
        rows += [run_case(backend, c) for c in CASES[backend]]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "matrix.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md = _markdown(rows)
    (RESULTS / "matrix.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
