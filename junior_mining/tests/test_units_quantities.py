"""Unit tests: printed-number parsing, precision intervals, dates, target windows."""

from decimal import Decimal

from jmi.quantities import (as_of_dates, interval, overlaps, parse_date, parse_number, quantize, target_window)


def test_parse_number_variants():
    assert parse_number("1,234.50").value == Decimal("1234.50")
    p = parse_number("(12.5)")
    assert p.value == Decimal("-12.5") and "parentheses read as negative" in p.transformations
    assert parse_number("0.62").decimals == 2


def test_ocr_suspect_is_not_corrected():
    for tok in ("1O.5", "2O1", "l23"):
        p = parse_number(tok)
        assert p.value is None and "OCR" in p.warnings[0]


def test_interval_is_centred_on_scaled_value():
    lo, hi = interval(Decimal("412000000"), 0, 6)
    assert (lo, hi) == (Decimal("411500000"), Decimal("412500000"))
    assert overlaps(interval(Decimal("920000"), 0, 3), interval(Decimal("920000"), 2, 6))   # 920 koz vs 0.92 Moz
    assert not overlaps(interval(Decimal("412000000"), 0, 6), interval(Decimal("432000000"), 0, 6))


def test_rounding_is_half_even_at_display():
    assert quantize(Decimal("0.725"), 2) == Decimal("0.72")
    assert quantize(Decimal("0.735"), 2) == Decimal("0.74")


def test_dates_across_line_breaks_and_as_of_phrases():
    assert parse_date("As at August 31,\n2026, there were") == "2026-08-31"
    assert parse_date("30 September 2026") == "2026-09-30"
    assert as_of_dates("As at August 31, 2026, ... expiring March 31, 2027") == ["2026-08-31"]


def test_target_windows_only_for_unambiguous_forms():
    assert target_window("in Q2 2027")[:2] == ("2027-04-01", "2027-06-30")
    assert target_window("in H2 2027")[:2] == ("2027-07-01", "2027-12-31")
    assert target_window("by the end of 2027")[1] == "2027-12-31"
    s, e, note = target_window("in mid-2027")
    assert s is None and e is None and "reviewer" in note
