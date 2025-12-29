"""Unit tests for business day calculations.

Tests TRID-compliant business day calculations including:
- Federal holiday handling
- Weekend exclusion
- Business day arithmetic
"""

import pytest
from datetime import date

from packages.compliance.business_days import (
    is_business_day,
    add_business_days,
    subtract_business_days,
    count_business_days_between,
    get_next_business_day,
    get_previous_business_day,
    get_federal_holidays,
    trid_loan_estimate_deadline,
    trid_closing_disclosure_deadline,
    _get_nth_weekday,
)


class TestGetNthWeekday:
    """Tests for finding nth weekday of a month."""

    def test_first_monday_january_2024(self):
        """First Monday in January 2024 is the 1st."""
        result = _get_nth_weekday(2024, 1, 1, 0)  # 0 = Monday
        assert result == date(2024, 1, 1)

    def test_third_monday_january_2024(self):
        """Third Monday in January 2024 is the 15th (MLK Day)."""
        result = _get_nth_weekday(2024, 1, 3, 0)
        assert result == date(2024, 1, 15)

    def test_last_monday_may_2024(self):
        """Last Monday in May 2024 is the 27th (Memorial Day)."""
        result = _get_nth_weekday(2024, 5, -1, 0)
        assert result == date(2024, 5, 27)

    def test_fourth_thursday_november_2024(self):
        """Fourth Thursday in November 2024 is the 28th (Thanksgiving)."""
        result = _get_nth_weekday(2024, 11, 4, 3)  # 3 = Thursday
        assert result == date(2024, 11, 28)


class TestGetFederalHolidays:
    """Tests for federal holiday detection."""

    def test_includes_new_years(self):
        """New Year's Day is a federal holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 1, 1) in holidays

    def test_includes_mlk_day(self):
        """MLK Day (third Monday in January) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 1, 15) in holidays

    def test_includes_presidents_day(self):
        """Presidents Day (third Monday in February) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 2, 19) in holidays

    def test_includes_memorial_day(self):
        """Memorial Day (last Monday in May) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 5, 27) in holidays

    def test_includes_juneteenth(self):
        """Juneteenth (June 19) is a holiday since 2021."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 6, 19) in holidays

    def test_juneteenth_not_before_2021(self):
        """Juneteenth was not a federal holiday before 2021."""
        holidays = get_federal_holidays(2020)
        assert date(2020, 6, 19) not in holidays

    def test_includes_independence_day(self):
        """Independence Day (July 4) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 7, 4) in holidays

    def test_includes_labor_day(self):
        """Labor Day (first Monday in September) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 9, 2) in holidays

    def test_includes_columbus_day(self):
        """Columbus Day (second Monday in October) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 10, 14) in holidays

    def test_includes_veterans_day(self):
        """Veterans Day (November 11) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 11, 11) in holidays

    def test_includes_thanksgiving(self):
        """Thanksgiving (fourth Thursday in November) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 11, 28) in holidays

    def test_includes_christmas(self):
        """Christmas Day (December 25) is a holiday."""
        holidays = get_federal_holidays(2024)
        assert date(2024, 12, 25) in holidays

    def test_saturday_holiday_observed_friday(self):
        """When a fixed holiday falls on Saturday, Friday is observed."""
        # July 4, 2026 falls on Saturday
        holidays = get_federal_holidays(2026)
        assert date(2026, 7, 3) in holidays  # Friday observed

    def test_sunday_holiday_observed_monday(self):
        """When a fixed holiday falls on Sunday, Monday is observed."""
        # July 4, 2027 falls on Sunday
        holidays = get_federal_holidays(2027)
        assert date(2027, 7, 5) in holidays  # Monday observed


class TestIsBusinessDay:
    """Tests for checking if a date is a business day."""

    def test_weekday_non_holiday_is_business_day(self):
        """A regular weekday is a business day."""
        assert is_business_day(date(2024, 6, 3))  # Monday, not a holiday

    def test_saturday_is_not_business_day(self):
        """Saturday is not a business day."""
        assert not is_business_day(date(2024, 6, 1))

    def test_sunday_is_not_business_day(self):
        """Sunday is not a business day."""
        assert not is_business_day(date(2024, 6, 2))

    def test_federal_holiday_is_not_business_day(self):
        """Federal holidays are not business days."""
        assert not is_business_day(date(2024, 7, 4))  # Independence Day

    def test_day_after_holiday_is_business_day(self):
        """Day after holiday (if weekday) is a business day."""
        assert is_business_day(date(2024, 7, 5))  # Friday after July 4


class TestAddBusinessDays:
    """Tests for adding business days to a date."""

    def test_add_zero_days_returns_same_date(self):
        """Adding zero business days returns the same date."""
        start = date(2024, 6, 3)
        assert add_business_days(start, 0) == start

    def test_add_one_business_day(self):
        """Adding one business day advances to next business day."""
        start = date(2024, 6, 3)  # Monday
        assert add_business_days(start, 1) == date(2024, 6, 4)  # Tuesday

    def test_add_business_days_skips_weekend(self):
        """Adding business days skips weekends."""
        start = date(2024, 5, 31)  # Friday
        assert add_business_days(start, 1) == date(2024, 6, 3)  # Monday

    def test_add_three_business_days_trid_example(self):
        """TRID: 3 business days from Monday is Thursday."""
        start = date(2024, 6, 3)  # Monday
        assert add_business_days(start, 3) == date(2024, 6, 6)  # Thursday

    def test_add_business_days_skips_holiday(self):
        """Adding business days skips federal holidays."""
        start = date(2024, 7, 2)  # Tuesday before July 4
        # July 4 (Thursday) is a holiday
        # 3 business days: Wed (1), skip Thu, Fri (2), Mon (3)
        assert add_business_days(start, 3) == date(2024, 7, 8)

    def test_negative_business_days(self):
        """Negative business days go backwards."""
        start = date(2024, 6, 6)  # Thursday
        assert add_business_days(start, -1) == date(2024, 6, 5)  # Wednesday


class TestSubtractBusinessDays:
    """Tests for subtracting business days from a date."""

    def test_subtract_three_business_days(self):
        """TRID: Closing Disclosure must be 3 business days before closing."""
        closing = date(2024, 6, 7)  # Friday
        # 3 business days before: Thu (1), Wed (2), Tue (3)
        assert subtract_business_days(closing, 3) == date(2024, 6, 4)  # Tuesday

    def test_subtract_across_weekend(self):
        """Subtracting business days handles weekends."""
        end = date(2024, 6, 3)  # Monday
        # 1 business day before Monday is Friday
        assert subtract_business_days(end, 1) == date(2024, 5, 31)

    def test_subtract_across_holiday(self):
        """Subtracting business days handles holidays."""
        end = date(2024, 7, 8)  # Monday after July 4
        # 3 business days back: Fri (1), skip Thu holiday, Wed (2), Tue (3)
        assert subtract_business_days(end, 3) == date(2024, 7, 2)


class TestCountBusinessDaysBetween:
    """Tests for counting business days between dates."""

    def test_count_same_day_returns_zero(self):
        """Same day returns zero business days."""
        d = date(2024, 6, 3)
        assert count_business_days_between(d, d) == 0

    def test_count_adjacent_business_days(self):
        """Adjacent business days count as 1."""
        assert count_business_days_between(date(2024, 6, 3), date(2024, 6, 4)) == 1

    def test_count_across_weekend(self):
        """Counting across weekend excludes Saturday and Sunday."""
        # Friday to Monday: only Monday is counted (end is inclusive)
        assert count_business_days_between(date(2024, 5, 31), date(2024, 6, 3)) == 1

    def test_count_across_holiday(self):
        """Counting across holiday excludes the holiday."""
        # July 2 to July 5: Wed (1), Thu=holiday skip, Fri (2) = 2 days
        assert count_business_days_between(date(2024, 7, 2), date(2024, 7, 5)) == 2

    def test_count_full_week(self):
        """Full business week has 5 business days."""
        assert count_business_days_between(date(2024, 5, 31), date(2024, 6, 7)) == 5


class TestGetNextBusinessDay:
    """Tests for getting the next business day."""

    def test_weekday_returns_same_date(self):
        """A business day returns itself."""
        assert get_next_business_day(date(2024, 6, 3)) == date(2024, 6, 3)

    def test_saturday_returns_monday(self):
        """Saturday returns next Monday."""
        assert get_next_business_day(date(2024, 6, 1)) == date(2024, 6, 3)

    def test_sunday_returns_monday(self):
        """Sunday returns next Monday."""
        assert get_next_business_day(date(2024, 6, 2)) == date(2024, 6, 3)

    def test_holiday_returns_next_business_day(self):
        """Holiday returns next business day."""
        assert get_next_business_day(date(2024, 7, 4)) == date(2024, 7, 5)


class TestGetPreviousBusinessDay:
    """Tests for getting the previous business day."""

    def test_weekday_returns_same_date(self):
        """A business day returns itself."""
        assert get_previous_business_day(date(2024, 6, 3)) == date(2024, 6, 3)

    def test_saturday_returns_friday(self):
        """Saturday returns previous Friday."""
        assert get_previous_business_day(date(2024, 6, 1)) == date(2024, 5, 31)

    def test_sunday_returns_friday(self):
        """Sunday returns previous Friday."""
        assert get_previous_business_day(date(2024, 6, 2)) == date(2024, 5, 31)


class TestTridFunctions:
    """Tests for TRID-specific deadline calculations."""

    def test_loan_estimate_deadline(self):
        """Loan Estimate due 3 business days after application."""
        application = date(2024, 6, 3)  # Monday
        assert trid_loan_estimate_deadline(application) == date(2024, 6, 6)

    def test_closing_disclosure_deadline(self):
        """Closing Disclosure due 3 business days before closing."""
        closing = date(2024, 6, 7)  # Friday
        assert trid_closing_disclosure_deadline(closing) == date(2024, 6, 4)

    def test_trid_with_holiday(self):
        """TRID deadlines properly handle holidays."""
        # If application is July 1 (Monday), LE due by:
        # July 2 (1), July 3 (2), skip July 4, July 5 (3)
        application = date(2024, 7, 1)
        assert trid_loan_estimate_deadline(application) == date(2024, 7, 5)
