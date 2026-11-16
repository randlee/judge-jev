"""A controlled UTC clock for date-path tests; no wall-clock reads."""
import datetime
from types import SimpleNamespace
from unittest import mock

FIXED_UTC = datetime.datetime(2026, 11, 13, 23, 59, 59, 999999, tzinfo=datetime.timezone.utc)


def utc_clock():
    clock = mock.Mock(wraps=datetime.datetime)
    clock.now.return_value = FIXED_UTC
    return SimpleNamespace(datetime=clock, timezone=datetime.timezone)
