"""Reprice historical usage against available electricity plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from models import ElectricityPlan, UsageRecord, db


@dataclass
class MonthlyUsage:
    year: int
    month: int
    total_kwh: float
    days: int


@dataclass
class PlanCostEstimate:
    plan: ElectricityPlan
    monthly_costs: list[dict]  # [{year, month, kwh, estimated_cost}, ...]
    total_cost: float
    avg_monthly_cost: float
    avg_price_per_kwh: float  # cents


def get_monthly_usage(esiid: str, start: date | None = None, end: date | None = None) -> list[MonthlyUsage]:
    """Aggregate daily usage into monthly totals."""
    query = UsageRecord.query.filter_by(esiid=esiid)
    if start:
        query = query.filter(UsageRecord.date >= start)
    if end:
        query = query.filter(UsageRecord.date <= end)

    records = query.order_by(UsageRecord.date).all()

    monthly: dict[tuple[int, int], MonthlyUsage] = {}
    for rec in records:
        key = (rec.date.year, rec.date.month)
        if key not in monthly:
            monthly[key] = MonthlyUsage(year=key[0], month=key[1], total_kwh=0.0, days=0)
        monthly[key].total_kwh += rec.usage_kwh
        monthly[key].days += 1

    return sorted(monthly.values(), key=lambda m: (m.year, m.month))


def reprice_usage(
    esiid: str,
    plan_ids: list[int] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> list[PlanCostEstimate]:
    """Calculate what historical usage would cost under each selected plan.

    If plan_ids is None, all plans in the database are used.
    """
    monthly_usage = get_monthly_usage(esiid, start, end)
    if not monthly_usage:
        return []

    if plan_ids:
        plans = ElectricityPlan.query.filter(ElectricityPlan.id.in_(plan_ids)).all()
    else:
        plans = ElectricityPlan.query.all()

    results = []
    for plan in plans:
        monthly_costs = []
        total = 0.0
        total_kwh = 0.0

        for mu in monthly_usage:
            cost = plan.estimate_monthly_cost(mu.total_kwh)
            if cost is not None:
                monthly_costs.append(
                    {
                        "year": mu.year,
                        "month": mu.month,
                        "kwh": round(mu.total_kwh, 2),
                        "estimated_cost": round(cost, 2),
                    }
                )
                total += cost
                total_kwh += mu.total_kwh

        num_months = len(monthly_costs) or 1
        avg_monthly = total / num_months
        avg_price = (total / total_kwh * 100) if total_kwh > 0 else 0

        results.append(
            PlanCostEstimate(
                plan=plan,
                monthly_costs=monthly_costs,
                total_cost=round(total, 2),
                avg_monthly_cost=round(avg_monthly, 2),
                avg_price_per_kwh=round(avg_price, 2),
            )
        )

    results.sort(key=lambda r: r.total_cost)
    return results
