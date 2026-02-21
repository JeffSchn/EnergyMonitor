"""Parse Smart Meter Texas CSV exports into UsageRecord rows."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import TextIO


@dataclass
class ParsedUsageRow:
    esiid: str
    date: date
    usage_kwh: float
    reading_type: str  # C or G
    actual_estimated: str  # A or E


def parse_daily_csv(file: TextIO) -> list[ParsedUsageRow]:
    """Parse a Smart Meter Texas *Daily* usage CSV.

    Expected columns (order may vary):
        ESIID, Date, Reading Type, Meter Reading (kWh), Actual/Estimated

    The file may include header metadata lines before the actual CSV header.
    We detect the header row by looking for a row that contains 'ESIID'.
    """
    content = file.read()
    lines = content.splitlines()

    # Find the header row
    header_idx = None
    for i, line in enumerate(lines):
        if "ESIID" in line.upper():
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find header row containing 'ESIID'. "
            "Please upload a daily usage CSV from Smart Meter Texas."
        )

    csv_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))

    # Normalize column names: strip whitespace and lowercase
    rows: list[ParsedUsageRow] = []
    for raw_row in reader:
        row = {k.strip().upper(): v.strip() for k, v in raw_row.items() if k}
        esiid = _get_field(row, ["ESIID", "ESI ID", "ELECTRIC SERVICE IDENTIFIER"])
        date_str = _get_field(row, ["DATE", "READ DATE", "USAGE DATE"])
        kwh_str = _get_field(
            row, ["METER READING (KWH)", "METER READING", "USAGE (KWH)", "KWH", "USAGE_KWH"]
        )
        reading_type = _get_field(row, ["READING TYPE", "TYPE"], default="C")
        actual_est = _get_field(row, ["ACTUAL/ESTIMATED", "ACTUAL_ESTIMATED"], default="A")

        parsed_date = _parse_date(date_str)
        usage_kwh = float(kwh_str)

        rows.append(
            ParsedUsageRow(
                esiid=esiid,
                date=parsed_date,
                usage_kwh=usage_kwh,
                reading_type=reading_type[0].upper() if reading_type else "C",
                actual_estimated=actual_est[0].upper() if actual_est else "A",
            )
        )

    return rows


def parse_interval_csv(file: TextIO) -> list[ParsedUsageRow]:
    """Parse a Smart Meter Texas 15-minute interval CSV into daily totals.

    Interval CSVs have columns: ESIID, Date, then 96 interval readings
    (one per 15-minute period). We sum them to get daily kWh.
    """
    content = file.read()
    lines = content.splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        if "ESIID" in line.upper():
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find header row containing 'ESIID'.")

    csv_text = "\n".join(lines[header_idx:])
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)

    rows: list[ParsedUsageRow] = []
    for raw_row in reader:
        if len(raw_row) < 3:
            continue
        esiid = raw_row[0].strip()
        date_str = raw_row[1].strip()
        # Columns 2..97 (or onward) are the 96 interval readings
        intervals = raw_row[2:]
        daily_kwh = sum(float(v) for v in intervals if v.strip())
        parsed_date = _parse_date(date_str)

        rows.append(
            ParsedUsageRow(
                esiid=esiid,
                date=parsed_date,
                usage_kwh=round(daily_kwh, 3),
                reading_type="C",
                actual_estimated="A",
            )
        )

    return rows


def _get_field(row: dict, candidates: list[str], default: str | None = None) -> str:
    for key in candidates:
        if key in row:
            return row[key]
    if default is not None:
        return default
    raise ValueError(f"Missing required column. Expected one of: {candidates}")


def _parse_date(date_str: str) -> date:
    """Try common date formats from SMT exports."""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str!r}")
