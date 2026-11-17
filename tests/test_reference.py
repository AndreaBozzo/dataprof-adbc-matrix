"""The exact reference must be right before it can grade dataprof."""

from __future__ import annotations

from fractions import Fraction

from matrix import reference


def test_statistics_are_exact_sample_moments():
    xs = [Fraction(v) for v in (1, 2, 2, -32768)]
    s = reference.statistics(xs)
    assert s["min"] == -32768 and s["max"] == 2
    assert s["mean"] == Fraction(-32763, 4)
    assert s["median"] == Fraction(3, 2)
    # Sample variance (n - 1), as dataprof reports it.
    assert s["variance"] == Fraction(805388290.75) / 3


def test_grades_separate_exact_f64_and_lost():
    exact = Fraction(9007199254740993)
    # dataprof reports floats: the nearest f64 to 2^53 + 1 is 2^53.
    assert reference.grade("max", exact, float(exact))[0] == "f64"
    assert reference.grade("max", Fraction(2), 2.0)[0] == "exact"
    assert reference.grade("variance", Fraction(4), 5.3333)[0] == "off"
    assert reference.grade("std_dev", Fraction(2), None)[0] == "off"
    assert reference.grade("std_dev", Fraction(2), None, null_ok=True)[0] == (
        "documented"
    )


def test_parse_keeps_decimal_digits_and_float_storage():
    assert reference.parse("99999999999999999999.99", "exact") == Fraction(
        9999999999999999999999, 100
    )
    assert reference.parse("0.1", "float64") == Fraction(0.1)
    assert reference.parse("NULL", "exact") is None


def test_moments_keep_twelve_significant_digits_above_1e8():
    # dataprof 0.14.0 (#1201): a moment at or above 1e8 serializes at 12
    # significant digits of its float; below that, 4 decimal places.
    mean = Fraction(3074457345618258601) + Fraction(2, 3)
    assert reference.grade("mean", mean, 3074457345619999744.0)[0] == "exact"
    assert reference.grade("mean", mean, 3074457345618258432.0)[0] == "off"
    assert reference.grade("mean", Fraction(12345678, 100), 123456.78)[0] == "exact"
    # Data values keep 4 decimal places at any magnitude.
    assert (
        reference.grade("max", Fraction(3074457345618258601), 3074457345619999744.0)[0]
        == "off"
    )


def test_exact_order_statistics_are_graded_as_strings():
    exact = Fraction(9223372036854775807)
    assert reference.grade_exact("max", exact, "9223372036854775807")[0] == "exact"
    assert reference.grade_exact("max", exact, "9223372036854775808")[0] == "off"
    assert reference.grade_exact("median", Fraction(19, 2), "9.5")[0] == "exact"
