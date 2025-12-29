"""Business day calculator with federal holiday support.

This module provides TRID-compliant business day calculations for
real estate transaction deadlines. It properly excludes weekends
and federal holidays as required by RESPA/TRID regulations.
"""

from datetime import date, timedelta
from functools import lru_cache


# Federal holidays observed for business day calculations
# These follow the federal holiday schedule per 5 U.S.C. § 6103
FEDERAL_HOLIDAYS = {
    # (month, day) for fixed holidays
    "new_years": (1, 1),
    "independence_day": (7, 4),
    "veterans_day": (11, 11),
    "christmas": (12, 25),
}

# Holidays that fall on specific weekday occurrences
FLOATING_HOLIDAYS = {
    "mlk_day": (1, 3, 0),  # Third Monday in January
    "presidents_day": (2, 3, 0),  # Third Monday in February
    "memorial_day": (5, -1, 0),  # Last Monday in May
    "labor_day": (9, 1, 0),  # First Monday in September
    "columbus_day": (10, 2, 0),  # Second Monday in October
    "thanksgiving": (11, 4, 3),  # Fourth Thursday in November
}


def _get_nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
    """Get the nth occurrence of a weekday in a month.

    Args:
        year: The year
        month: The month (1-12)
        n: Which occurrence (1=first, 2=second, etc., -1=last)
        weekday: Day of week (0=Monday, 6=Sunday)

    Returns:
        The date of the nth weekday
    """
    if n > 0:
        # Find first occurrence
        first_day = date(year, month, 1)
        days_until = (weekday - first_day.weekday()) % 7
        first_occurrence = first_day + timedelta(days=days_until)
        return first_occurrence + timedelta(weeks=n - 1)
    else:
        # Last occurrence - find first of next month, go back
        if month == 12:
            first_next = date(year + 1, 1, 1)
        else:
            first_next = date(year, month + 1, 1)
        last_day = first_next - timedelta(days=1)
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)


@lru_cache(maxsize=10)
def get_federal_holidays(year: int) -> set[date]:
    """Get all federal holidays for a given year.

    Args:
        year: The year to get holidays for

    Returns:
        Set of dates that are federal holidays
    """
    holidays = set()

    # Fixed holidays
    for holiday_name, (month, day) in FEDERAL_HOLIDAYS.items():
        holiday_date = date(year, month, day)

        # Handle observed holidays when falling on weekend
        if holiday_date.weekday() == 5:  # Saturday
            holidays.add(holiday_date - timedelta(days=1))  # Observed Friday
        elif holiday_date.weekday() == 6:  # Sunday
            holidays.add(holiday_date + timedelta(days=1))  # Observed Monday
        else:
            holidays.add(holiday_date)

    # Floating holidays
    for holiday_name, (month, occurrence, weekday) in FLOATING_HOLIDAYS.items():
        holiday_date = _get_nth_weekday(year, month, occurrence, weekday)
        holidays.add(holiday_date)

    # Juneteenth (June 19) - Federal holiday since 2021
    if year >= 2021:
        juneteenth = date(year, 6, 19)
        if juneteenth.weekday() == 5:
            holidays.add(juneteenth - timedelta(days=1))
        elif juneteenth.weekday() == 6:
            holidays.add(juneteenth + timedelta(days=1))
        else:
            holidays.add(juneteenth)

    return holidays


def is_business_day(check_date: date) -> bool:
    """Check if a date is a business day.

    A business day is any day that is not:
    - Saturday
    - Sunday
    - A federal holiday

    Args:
        check_date: The date to check

    Returns:
        True if the date is a business day
    """
    # Weekend check
    if check_date.weekday() >= 5:
        return False

    # Holiday check
    holidays = get_federal_holidays(check_date.year)
    return check_date not in holidays


def add_business_days(start_date: date, business_days: int) -> date:
    """Add business days to a date.

    This is TRID-compliant for calculating deadlines like:
    - Loan Estimate delivery (3 business days from application)
    - Closing Disclosure delivery (3 business days before closing)

    Args:
        start_date: The starting date
        business_days: Number of business days to add (can be negative)

    Returns:
        The resulting date after adding business days
    """
    if business_days == 0:
        return start_date

    direction = 1 if business_days > 0 else -1
    remaining = abs(business_days)
    current = start_date

    while remaining > 0:
        current += timedelta(days=direction)
        if is_business_day(current):
            remaining -= 1

    return current


def subtract_business_days(end_date: date, business_days: int) -> date:
    """Subtract business days from a date.

    Commonly used for "X business days before closing" calculations.

    Args:
        end_date: The ending date
        business_days: Number of business days to subtract

    Returns:
        The resulting date
    """
    return add_business_days(end_date, -business_days)


def count_business_days_between(start_date: date, end_date: date) -> int:
    """Count the number of business days between two dates.

    The start date is not counted, but the end date is.

    Args:
        start_date: The starting date (exclusive)
        end_date: The ending date (inclusive)

    Returns:
        Number of business days between the dates
    """
    if start_date >= end_date:
        return 0

    count = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if is_business_day(current):
            count += 1
        current += timedelta(days=1)

    return count


def get_next_business_day(check_date: date) -> date:
    """Get the next business day on or after the given date.

    Args:
        check_date: The date to check

    Returns:
        The next business day (could be the same date)
    """
    current = check_date
    while not is_business_day(current):
        current += timedelta(days=1)
    return current


def get_previous_business_day(check_date: date) -> date:
    """Get the previous business day on or before the given date.

    Args:
        check_date: The date to check

    Returns:
        The previous business day (could be the same date)
    """
    current = check_date
    while not is_business_day(current):
        current -= timedelta(days=1)
    return current


# Convenience aliases for TRID-specific calculations
def trid_loan_estimate_deadline(application_date: date) -> date:
    """Calculate Loan Estimate delivery deadline (3 business days).

    Per TRID (12 CFR 1026.19(e)), the Loan Estimate must be
    delivered within 3 business days of receiving an application.

    Args:
        application_date: Date the loan application was received

    Returns:
        Latest date to deliver Loan Estimate
    """
    return add_business_days(application_date, 3)


def trid_closing_disclosure_deadline(closing_date: date) -> date:
    """Calculate Closing Disclosure delivery deadline.

    Per TRID (12 CFR 1026.19(f)), the Closing Disclosure must be
    received by the consumer at least 3 business days before closing.

    Args:
        closing_date: Scheduled closing date

    Returns:
        Latest date consumer must receive Closing Disclosure
    """
    return subtract_business_days(closing_date, 3)
