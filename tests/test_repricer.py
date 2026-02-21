"""Tests for the repricing engine."""

import pytest

from app import create_app
from config import Config
from models import ElectricityPlan, UsageRecord, db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        _seed_data()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_data():
    from datetime import date

    # Seed usage records for 3 months
    import calendar

    esiid = "1234567890123"
    for month in (1, 2, 3):
        days_in_month = calendar.monthrange(2025, month)[1]
        for day in range(1, days_in_month + 1):
            db.session.add(
                UsageRecord(
                    esiid=esiid,
                    date=date(2025, month, day),
                    usage_kwh=40.0,  # flat 40 kWh/day
                    reading_type="C",
                    actual_estimated="A",
                )
            )

    # Seed a simple plan: 10 cents/kWh at 1000 tier
    db.session.add(
        ElectricityPlan(
            plan_id="test-plan-1",
            company_name="Test Energy Co",
            plan_name="Simple Fixed",
            plan_type="Fixed",
            price_kwh_500=12.0,
            price_kwh_1000=10.0,
            price_kwh_2000=9.0,
        )
    )
    db.session.commit()


def test_reprice_produces_results(app):
    from services.repricer import reprice_usage

    with app.app_context():
        results = reprice_usage("1234567890123")
        assert len(results) == 1
        r = results[0]
        assert r.plan.plan_id == "test-plan-1"
        assert r.total_cost > 0
        assert len(r.monthly_costs) == 3


def test_dashboard_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_upload_page_loads(client):
    resp = client.get("/upload")
    assert resp.status_code == 200
    assert b"Upload" in resp.data


def test_api_usage(client):
    resp = client.get("/api/usage?esiid=1234567890123")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["data"]) == 90  # Jan + Feb + Mar 2025 = 31+28+31
