"""Client for the Power to Choose API and CSV export."""

from __future__ import annotations

import csv
import io
from datetime import datetime

import requests

from config import Config
from models import ElectricityPlan, db


def fetch_plans_from_api(zip_code: str = "") -> list[dict]:
    """Fetch plans from the Power to Choose REST API.

    POST http://api.powertochoose.org/api/PowerToChoose/plans
    Body: {"zip_code": "77001", "page_size": 200}
    """
    payload = {"zip_code": zip_code, "page_size": 200}
    resp = requests.post(Config.PTC_API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def fetch_plans_csv() -> list[dict]:
    """Download the full plan list as CSV from Power to Choose."""
    resp = requests.get(Config.PTC_CSV_URL, timeout=30)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    return [row for row in reader]


def save_plans_to_db(raw_plans: list[dict]) -> int:
    """Upsert raw API plan records into the database.

    Returns the number of plans saved.
    """
    count = 0
    now = datetime.utcnow()

    for p in raw_plans:
        plan_id = str(p.get("plan_id") or p.get("idKey") or p.get("[idKey]", ""))
        if not plan_id:
            continue

        existing = ElectricityPlan.query.filter_by(plan_id=plan_id).first()
        plan = existing or ElectricityPlan(plan_id=plan_id)

        plan.company_name = p.get("company_name", p.get("[Company Name]", ""))
        plan.plan_name = p.get("plan_name", p.get("[Plan Name]", ""))
        plan.plan_type = p.get("plan_type", p.get("[Plan Type]", ""))
        plan.contract_length = _safe_int(p.get("contract_length") or p.get("[Term Value]"))
        plan.price_kwh_500 = _safe_float(p.get("price_kwh500") or p.get("[Price/kWh 500]"))
        plan.price_kwh_1000 = _safe_float(p.get("price_kwh1000") or p.get("[Price/kWh 1000]"))
        plan.price_kwh_2000 = _safe_float(p.get("price_kwh2000") or p.get("[Price/kWh 2000]"))
        plan.base_charge = _safe_float(p.get("base_charge") or p.get("[Base Charge]"))
        plan.cancellation_fee = _safe_float(
            p.get("cancellation_fee") or p.get("[Early Termination/Cancel Fee]")
        )
        plan.renewable_pct = _safe_float(p.get("renewable_pct") or p.get("[Renewable %]"))
        plan.is_time_of_use = bool(p.get("timeofuse") or p.get("[Time of Use]"))
        plan.fetched_at = now

        if not existing:
            db.session.add(plan)
        count += 1

    db.session.commit()
    return count


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").replace("$", "").replace("¢", "").strip())
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None
