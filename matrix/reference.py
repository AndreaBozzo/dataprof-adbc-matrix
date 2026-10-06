"""Exact reference statistics for numeric cases, computed from the SQL literals.

The reference never goes through the database or Arrow: it parses the literals
the case inserts and computes with exact rationals. Each serialized dataprof
statistic is then graded against it:

- ``exact``: equals the true value at dataprof's serialized precision.
- ``f64``: differs from the true value, but equals the true value rounded to
  the nearest f64 first. No f64-based profiler can do better.
- ``off``: worse than the nearest f64, so precision was lost on the way.

The Arrow column is checked against the same literals, which separates loss in
the driver from loss in dataprof.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

import pyarrow as pa

# dataprof serializes statistics and extrema to 4 decimal places, ties away
# from zero (docs/schema/README.md, numeric equality contract).
QUANTUM = Decimal("0.0001")
# Enough digits to hold any finite f64 to 4 decimal places.
PREC = 400
STATS = ("min", "max", "mean", "median", "variance", "std_dev")


def parse(literal: str, kind: str) -> Fraction | None:
    """Value stored for ``literal`` in a column of ``kind`` (exact or float64)."""
    s = literal.strip()
    if s.upper() == "NULL":
        return None
    s = s.strip("'")
    if kind == "float64":
        return Fraction(float(s))
    return Fraction(Decimal(s))


def _sqrt(x: Fraction) -> Fraction:
    with localcontext() as ctx:
        ctx.prec = PREC
        return Fraction(_to_decimal(x).sqrt())


def _to_decimal(x: Fraction) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = PREC
        return Decimal(x.numerator) / Decimal(x.denominator)


def statistics(values: list[Fraction]) -> dict[str, Fraction]:
    xs = sorted(values)
    n = len(xs)
    mean = sum(xs, Fraction(0)) / n
    mid = n // 2
    median = xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2
    variance = (
        sum(((x - mean) ** 2 for x in xs), Fraction(0)) / (n - 1)
        if n > 1
        else Fraction(0)
    )
    return {
        "min": xs[0],
        "max": xs[-1],
        "mean": mean,
        "median": median,
        "variance": variance,
        "std_dev": _sqrt(variance),
    }


def _quantize(d: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = PREC
        return d.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def _serialized(x: Fraction) -> Decimal:
    return _quantize(_to_decimal(x))


def fits_f64(x: Fraction) -> bool:
    return _nearest_f64(x) is not None


def _nearest_f64(x: Fraction) -> Fraction | None:
    try:
        return Fraction(float(x))
    except OverflowError:
        return None


def grade(
    name: str, exact: Fraction, observed, null_ok: bool = False
) -> tuple[str, str, float]:
    """Return (grade, detail, relative error) for one serialized statistic.

    ``null_ok`` marks a null the output contract documents even though the
    value itself fits an f64 (std_dev when the variance overflows).
    """
    near = _nearest_f64(exact)
    if observed is None:
        # The contract reports null when the value cannot be a finite f64.
        if near is None:
            return "f64", "", 0.0
        if null_ok:
            return "documented", "", 0.0
        return "off", f"{name} absent (exact {_to_decimal(exact):.20g})", 1.0
    obs = _quantize(Decimal(observed))
    if obs == _serialized(exact):
        return "exact", "", 0.0
    detail = f"{name} {obs.normalize():f} vs exact {_serialized(exact).normalize():f}"
    rel = float(abs(Fraction(obs) - exact) / abs(exact)) if exact else 1.0
    detail += f" (rel {rel:.1e})"
    if near is not None and obs == _serialized(near):
        return "f64", detail + " nearest f64", rel
    return "off", detail, rel


def arrow_values(batches: list[pa.RecordBatch]) -> list:
    out = []
    for b in batches:
        col = b.column(0)
        if isinstance(col.type, pa.ExtensionType):
            col = col.storage
        out += col.to_pylist()
    return out


def arrow_loss(literals: list[str], kind: str, values: list) -> list[str]:
    """Rows where the Arrow value differs from the inserted literal."""
    lost = []
    for lit, got in zip(literals, values, strict=True):
        want = parse(lit, kind)
        if got is None or want is None:
            if (got is None) != (want is None):
                lost.append(f"{lit} -> {got!r}")
            continue
        have = Fraction(Decimal(got)) if isinstance(got, str) else Fraction(got)
        if have != want:
            lost.append(f"{lit} -> {got!r}")
    return lost
