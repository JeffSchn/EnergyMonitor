"""Energy Monitor - Flask application entry point."""

from __future__ import annotations

import io
import os
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from config import Config
from models import ElectricityPlan, UsageRecord, db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @app.route("/")
    def dashboard():
        total_records = UsageRecord.query.count()
        plan_count = ElectricityPlan.query.count()

        first = UsageRecord.query.order_by(UsageRecord.date.asc()).first()
        last = UsageRecord.query.order_by(UsageRecord.date.desc()).first()
        if first and last:
            date_range = f"{first.date} to {last.date}"
        else:
            date_range = "No data"

        avg_daily_kwh = 0.0
        if total_records:
            result = db.session.query(db.func.avg(UsageRecord.usage_kwh)).scalar()
            avg_daily_kwh = round(result or 0, 1)

        monthly_data = _get_monthly_aggregates()

        return render_template(
            "index.html",
            total_records=total_records,
            date_range=date_range,
            avg_daily_kwh=avg_daily_kwh,
            plan_count=plan_count,
            monthly_data=monthly_data,
        )

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        result = None
        if request.method == "POST":
            csv_file = request.files.get("csv_file")
            file_type = request.form.get("file_type", "daily")

            if not csv_file or csv_file.filename == "":
                flash("Please select a CSV file.", "error")
                return redirect(url_for("upload"))

            from services.csv_parser import parse_daily_csv, parse_interval_csv

            try:
                text = csv_file.stream.read().decode("utf-8-sig")
                file_obj = io.StringIO(text)

                if file_type == "interval":
                    rows = parse_interval_csv(file_obj)
                else:
                    rows = parse_daily_csv(file_obj)

                imported, skipped = _upsert_usage_rows(rows)
                result = {"imported": imported, "skipped": skipped}
                flash(f"Imported {imported} records ({skipped} duplicates skipped).", "success")
            except Exception as e:
                flash(f"Error parsing CSV: {e}", "error")

        return render_template("upload.html", result=result)

    # ------------------------------------------------------------------
    # Usage visualization
    # ------------------------------------------------------------------
    @app.route("/usage")
    def usage_view():
        start = request.args.get("start", "")
        end = request.args.get("end", "")

        query = UsageRecord.query.order_by(UsageRecord.date.asc())
        if start:
            query = query.filter(UsageRecord.date >= date.fromisoformat(start))
        if end:
            query = query.filter(UsageRecord.date <= date.fromisoformat(end))

        records = query.all()

        daily_data = [{"date": r.date.isoformat(), "kwh": r.usage_kwh} for r in records]
        monthly_data = _aggregate_monthly(records)

        return render_template(
            "usage.html",
            records=records,
            daily_data=daily_data,
            monthly_data=monthly_data,
            start=start,
            end=end,
        )

    # ------------------------------------------------------------------
    # Plans
    # ------------------------------------------------------------------
    @app.route("/plans")
    def plans_view():
        plans = ElectricityPlan.query.order_by(ElectricityPlan.price_kwh_1000.asc()).all()
        return render_template("plans.html", plans=plans)

    @app.route("/plans/fetch", methods=["POST"])
    def fetch_plans():
        from services.ptc_client import fetch_plans_from_api, save_plans_to_db

        zip_code = request.form.get("zip_code", "")
        try:
            raw_plans = fetch_plans_from_api(zip_code)
            count = save_plans_to_db(raw_plans)
            flash(f"Fetched and saved {count} plans.", "success")
        except Exception as e:
            flash(f"Error fetching plans: {e}", "error")
        return redirect(url_for("plans_view"))

    # ------------------------------------------------------------------
    # Reprice
    # ------------------------------------------------------------------
    @app.route("/reprice", methods=["GET", "POST"])
    def reprice_view():
        esiids = [
            r[0] for r in db.session.query(UsageRecord.esiid).distinct().all()
        ]
        results = None
        reprice_chart_data = None
        selected_esiid = ""
        start = ""
        end = ""

        if request.method == "POST":
            from services.repricer import reprice_usage

            selected_esiid = request.form.get("esiid", "")
            start = request.form.get("start", "")
            end = request.form.get("end", "")

            start_date = date.fromisoformat(start) if start else None
            end_date = date.fromisoformat(end) if end else None

            results = reprice_usage(selected_esiid, start=start_date, end=end_date)

            # Prepare chart data (top 15 cheapest)
            top = results[:15]
            reprice_chart_data = {
                "labels": [f"{r.plan.company_name} - {r.plan.plan_name}"[:40] for r in top],
                "costs": [r.total_cost for r in top],
            }

        return render_template(
            "reprice.html",
            esiids=esiids,
            results=results,
            reprice_chart_data=reprice_chart_data,
            selected_esiid=selected_esiid,
            start=start,
            end=end,
        )

    # ------------------------------------------------------------------
    # API endpoints (JSON)
    # ------------------------------------------------------------------
    @app.route("/api/usage")
    def api_usage():
        esiid = request.args.get("esiid", "")
        query = UsageRecord.query
        if esiid:
            query = query.filter_by(esiid=esiid)
        records = query.order_by(UsageRecord.date.asc()).all()
        return {"data": [r.to_dict() for r in records]}

    @app.route("/api/plans")
    def api_plans():
        plans = ElectricityPlan.query.all()
        return {"data": [p.to_dict() for p in plans]}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _upsert_usage_rows(rows) -> tuple[int, int]:
    imported = 0
    skipped = 0
    for row in rows:
        existing = UsageRecord.query.filter_by(esiid=row.esiid, date=row.date).first()
        if existing:
            skipped += 1
            continue
        rec = UsageRecord(
            esiid=row.esiid,
            date=row.date,
            usage_kwh=row.usage_kwh,
            reading_type=row.reading_type,
            actual_estimated=row.actual_estimated,
        )
        db.session.add(rec)
        imported += 1
    db.session.commit()
    return imported, skipped


def _get_monthly_aggregates() -> list[dict]:
    records = UsageRecord.query.order_by(UsageRecord.date.asc()).all()
    return _aggregate_monthly(records)


def _aggregate_monthly(records) -> list[dict]:
    monthly: dict[str, float] = {}
    for rec in records:
        key = rec.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + rec.usage_kwh
    return [
        {"label": k, "kwh": round(v, 1)} for k, v in sorted(monthly.items())
    ]


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
