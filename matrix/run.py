"""Run every type case through ADBC into dataprof and write the matrix.

Usage: uv run python -m matrix.run [--backend sqlite|postgresql]

Each case runs twice, once with the driver's default batching and once with
tiny batches, and the two serialized column profiles must be identical. The
batch row counts the driver actually produced are recorded for both runs.

A full run writes results/. Every backend must be reachable, so a missing
PostgreSQL fails the run instead of dropping its rows. ``--backend`` runs a
subset and only prints, so it never overwrites the full results.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import dataprof

from matrix import reference
from matrix.backends import SMALL_BATCH_OPTIONS, connect, postgres_available, reader
from matrix.cases import CASES, Case

FLOAT64_RTOL = 1e-9
RESULTS = Path(__file__).resolve().parent.parent / "results"

PACKAGES = (
    "dataprof",
    "pyarrow",
    "adbc-driver-manager",
    "adbc-driver-sqlite",
    "adbc-driver-postgresql",
)


def _table_sql(backend: str, case: Case) -> list[str]:
    col = f"v {case.sql_type}".strip()
    stmts = ["DROP TABLE IF EXISTS t", f"CREATE TABLE t (id integer, {col})"]
    if case.values:
        rows = ", ".join(f"({i}, {v})" for i, v in enumerate(case.values))
        stmts.append(f"INSERT INTO t VALUES {rows}")
    return stmts


def _profile_column(backend: str, case: Case, options: dict | None):
    """Profile the case column; return (arrow type, batches, column, error).

    The query runs twice on the same table: once to keep the batches the
    driver emits under ``options``, once to profile the stream.
    """
    sql = "SELECT v FROM t ORDER BY id"
    with connect(backend) as conn:
        with conn.cursor() as cur:
            for stmt in _table_sql(backend, case):
                cur.execute(stmt)
            conn.commit()
        with conn.cursor() as cur:
            batches = list(reader(cur, sql, options))
        with conn.cursor() as cur:
            rbr = reader(cur, sql, options)
            arrow_type = str(rbr.schema.field(0).type)
            try:
                report = dataprof.profile(rbr)
            except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                return arrow_type, batches, None, f"{type(exc).__name__}: {exc}"
    return arrow_type, batches, report.to_dict()["columns"][0], None


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


def _check_reference(row: dict, case: Case, batches: list, col: dict) -> list[str]:
    """Grade counts and statistics against the exact reference of the literals.

    An exact-typed column (integer, decimal) must match the true value. An f64
    column may differ from it by f64 arithmetic: relative error up to
    FLOAT64_RTOL, the raw-value tolerance of dataprof's parity tests.
    """
    parsed = [reference.parse(v, case.reference) for v in case.values]
    present = [v for v in parsed if v is not None]
    problems = []
    lost = reference.arrow_loss(
        case.values, case.reference, reference.arrow_values(batches)
    )
    if lost:
        problems.append("driver changed values: " + ", ".join(lost))
    counts = {
        "total_count": len(parsed),
        "null_count": len(parsed) - len(present),
        "unique_count": len(set(present)),
    }
    for key, want in counts.items():
        if col.get(key) != want:
            problems.append(f"{key} {col.get(key)} vs exact {want}")
    stats = col.get("stats") or {}
    grades = {}
    exact_stats = reference.statistics(present)
    # Documented: std_dev is null whenever the variance overflows f64.
    variance_overflows = not reference.fits_f64(exact_stats["variance"])
    for name, exact in exact_stats.items():
        null_ok = name == "std_dev" and variance_overflows
        grade, detail, rel = reference.grade(name, exact, stats.get(name), null_ok)
        grades[name] = grade
        if not detail:
            continue
        if case.reference != "float64" or rel > FLOAT64_RTOL:
            problems.append(detail)
    row["reference_grades"] = grades
    return problems


def run_case(backend: str, case: Case) -> dict:
    row: dict = {
        "backend": backend,
        "case": case.name,
        "sql_type": case.sql_type,
        "note": case.note,
    }
    try:
        arrow_type, batches, col, err = _profile_column(backend, case, None)
    except Exception as exc:  # noqa: BLE001 - recorded in the matrix
        row.update(status="driver error", detail=f"{type(exc).__name__}: {exc}")
        return row
    row["arrow_type"] = arrow_type
    row["batches"] = {"default": [b.num_rows for b in batches]}
    if err:
        row.update(status="profile error", detail=err)
        return row
    row["observed"] = {
        k: col.get(k)
        for k in ("data_type", "total_count", "null_count", "unique_count")
    }
    row["observed"]["stats"] = col.get("stats")
    problems = _check(case.expect, col)
    if case.reference:
        problems += _check_reference(row, case, batches, col)

    try:
        _, small_batches, small, small_err = _profile_column(
            backend, case, SMALL_BATCH_OPTIONS[backend]
        )
        row["batches"]["small"] = [b.num_rows for b in small_batches]
    except Exception as exc:  # noqa: BLE001 - recorded in the matrix
        small, small_err = None, f"{type(exc).__name__}: {exc}"
    if small_err:
        problems.append(f"small batches: {small_err}")
    else:
        if len(case.values) > 1 and len(small_batches) < 2:
            row["batch_note"] = "small-batch run was not split, so it compares nothing"
        if small != col:
            diff = sorted(
                k for k in set(col) | set(small) if col.get(k) != small.get(k)
            )
            msg = f"small batches change {', '.join(diff)}"
            if case.driver_batch_variant:
                row["batch_note"] = msg + " (driver output differs)"
            else:
                problems.append(msg)

    row.update(status="ok" if not problems else "mismatch", detail="; ".join(problems))
    return row


def _server_version(backend: str) -> str:
    with connect(backend) as conn:
        return conn.adbc_get_info().get("vendor_version", "unknown")


def environment(backends: list[str]) -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {p: version(p) for p in PACKAGES},
        "servers": {b: _server_version(b) for b in backends},
    }


def _batches_cell(r: dict) -> str:
    b = r.get("batches") or {}
    if "default" not in b:
        return ""

    def fmt(rows: list[int]) -> str:
        return "+".join(map(str, rows)) or "0"

    small = fmt(b["small"]) if "small" in b else "?"
    return f"{fmt(b['default'])} / {small}"


def _markdown(env: dict, rows: list[dict]) -> str:
    pkgs = ", ".join(f"{k} {v}" for k, v in env["packages"].items())
    servers = ", ".join(f"{k} {v}" for k, v in env["servers"].items())
    out = [
        f"# ADBC matrix (dataprof {env['packages']['dataprof']})",
        "",
        f"Python {env['python']} on {env['platform']}.  ",
        f"Packages: {pkgs}.  ",
        f"Servers: {servers}.",
        "",
        (
            "Batches: rows per batch the driver emitted, default run / small-batch "
            "run. Notes marked (*) are caveats on an `ok` row."
        ),
        "",
        "| backend | case | Arrow type | dataprof type | batches | status | detail |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        dtype = (r.get("observed") or {}).get("data_type", "")
        parts = [r.get("detail") or ""]
        if r.get("batch_note"):
            parts.append(f"(*) {r['batch_note']}")
        detail = "; ".join(p for p in parts if p)
        detail = detail.replace("|", "\\|").replace("\n", " ")
        status = r["status"] + (" (*)" if r.get("batch_note") else "")
        out.append(
            f"| {r['backend']} | {r['case']} | `{r.get('arrow_type', '')}` "
            f"| {dtype} | {_batches_cell(r)} | {status} | {detail} |"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=sorted(CASES))
    args = ap.parse_args()
    backends = [args.backend] if args.backend else sorted(CASES)
    if "postgresql" in backends and not postgres_available():
        sys.exit("postgresql unreachable (docker compose up -d); nothing written")
    rows = []
    for backend in backends:
        rows += [run_case(backend, c) for c in CASES[backend]]
    env = environment(backends)
    md = _markdown(env, rows)
    print(md)
    if args.backend:
        print("subset run: results/ left unchanged")
        return
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "matrix.json").write_text(
        json.dumps({"environment": env, "rows": rows}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (RESULTS / "matrix.md").write_text(md, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
