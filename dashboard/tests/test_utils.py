from datetime import date
from decimal import Decimal

from django.test import TestCase

from dashboard.templatetags.number_format import numfmt
from dashboard.views import _count_occurrences


class CountOccurrencesTests(TestCase):
    def test_start_after_period_end_returns_zero(self):
        result = _count_occurrences(
            start_date=date(2025, 6, 1),
            interval_months=1,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 5, 31),
        )

        self.assertEqual(result, 0)

    def test_monthly_interval_within_period(self):
        result = _count_occurrences(
            start_date=date(2025, 1, 15),
            interval_months=1,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
        )

        self.assertEqual(result, 3)  # Jan 15, Feb 15, Mar 15

    def test_quarterly_interval_within_year(self):
        result = _count_occurrences(
            start_date=date(2025, 1, 1),
            interval_months=3,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
        )

        self.assertEqual(result, 4)  # Q1, Q2, Q3, Q4

    def test_start_before_period_skips_to_first_in_period(self):
        result = _count_occurrences(
            start_date=date(2024, 1, 1),
            interval_months=1,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 2, 28),
        )

        self.assertEqual(result, 2)  # Jan 1, Feb 1

    def test_yearly_interval_over_multiple_years(self):
        result = _count_occurrences(
            start_date=date(2020, 6, 1),
            interval_months=12,
            period_start=date(2023, 1, 1),
            period_end=date(2025, 12, 31),
        )

        self.assertEqual(result, 3)  # 2023-06-01, 2024-06-01, 2025-06-01


class NumfmtFilterTests(TestCase):
    def test_formats_integer_without_decimals(self):
        result = numfmt(Decimal("1000"))

        self.assertEqual(result, "1,000")

    def test_formats_decimal_with_two_places(self):
        result = numfmt(Decimal("1234.56"))

        self.assertEqual(result, "1,234.56")

    def test_strips_trailing_zeros(self):
        result = numfmt(Decimal("100.50"))

        self.assertEqual(result, "100.5")

    def test_returns_dash_for_none(self):
        result = numfmt(None)

        self.assertEqual(result, "-")

    def test_returns_dash_for_empty_string(self):
        result = numfmt("")

        self.assertEqual(result, "-")

    def test_returns_boolean_unchanged(self):
        result = numfmt(True)

        self.assertEqual(result, True)
