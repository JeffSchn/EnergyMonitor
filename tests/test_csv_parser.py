"""Tests for the Smart Meter Texas CSV parser."""

import io
from datetime import date

import pytest

from services.csv_parser import parse_daily_csv, parse_interval_csv


DAILY_CSV = """\
Smart Meter Texas - Daily Usage Report
Generated: 01/15/2025

ESIID,Date,Reading Type,Meter Reading (kWh),Actual/Estimated
1234567890123,01/01/2025,C,45.2,A
1234567890123,01/02/2025,C,38.7,A
1234567890123,01/03/2025,C,52.1,E
"""

INTERVAL_CSV = """\
ESIID,Date,00:15,00:30,00:45,01:00
1234567890123,01/01/2025,0.5,0.6,0.4,0.7
1234567890123,01/02/2025,0.3,0.5,0.6,0.8
"""


def test_parse_daily_csv():
    rows = parse_daily_csv(io.StringIO(DAILY_CSV))
    assert len(rows) == 3
    assert rows[0].esiid == "1234567890123"
    assert rows[0].date == date(2025, 1, 1)
    assert rows[0].usage_kwh == 45.2
    assert rows[0].reading_type == "C"
    assert rows[0].actual_estimated == "A"
    assert rows[2].actual_estimated == "E"


def test_parse_daily_csv_missing_header():
    with pytest.raises(ValueError, match="Could not find header"):
        parse_daily_csv(io.StringIO("no,useful,data\n1,2,3\n"))


def test_parse_interval_csv():
    rows = parse_interval_csv(io.StringIO(INTERVAL_CSV))
    assert len(rows) == 2
    assert rows[0].date == date(2025, 1, 1)
    assert rows[0].usage_kwh == pytest.approx(2.2, abs=0.01)
    assert rows[1].usage_kwh == pytest.approx(2.2, abs=0.01)
