from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UsageRecord(db.Model):
    """Daily electricity usage record from Smart Meter Texas."""

    __tablename__ = "usage_records"

    id = db.Column(db.Integer, primary_key=True)
    esiid = db.Column(db.String(22), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    usage_kwh = db.Column(db.Float, nullable=False)
    reading_type = db.Column(db.String(1), default="C")  # C=Consumption, G=Generation
    actual_estimated = db.Column(db.String(1), default="A")  # A=Actual, E=Estimated

    __table_args__ = (
        db.UniqueConstraint("esiid", "date", name="uq_esiid_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "esiid": self.esiid,
            "date": self.date.isoformat(),
            "usage_kwh": self.usage_kwh,
            "reading_type": self.reading_type,
            "actual_estimated": self.actual_estimated,
        }


class ElectricityPlan(db.Model):
    """Electricity plan from Power to Choose."""

    __tablename__ = "electricity_plans"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.String(50), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    plan_name = db.Column(db.String(200), nullable=False)
    plan_type = db.Column(db.String(50))  # Fixed, Variable, Indexed
    contract_length = db.Column(db.Integer)  # months
    rate_type = db.Column(db.String(50))

    # Prices at standard usage tiers (cents/kWh, includes TDU)
    price_kwh_500 = db.Column(db.Float)
    price_kwh_1000 = db.Column(db.Float)
    price_kwh_2000 = db.Column(db.Float)

    # Rate components for repricing
    base_charge = db.Column(db.Float, default=0.0)  # $/month
    energy_charge = db.Column(db.Float)  # $/kWh
    tdu_delivery_charge = db.Column(db.Float, default=0.0)  # $/month
    tdu_per_kwh = db.Column(db.Float, default=0.0)  # $/kWh

    # Plan details
    cancellation_fee = db.Column(db.Float)
    renewable_pct = db.Column(db.Float)
    is_time_of_use = db.Column(db.Boolean, default=False)
    fetched_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "company_name": self.company_name,
            "plan_name": self.plan_name,
            "plan_type": self.plan_type,
            "contract_length": self.contract_length,
            "price_kwh_500": self.price_kwh_500,
            "price_kwh_1000": self.price_kwh_1000,
            "price_kwh_2000": self.price_kwh_2000,
            "base_charge": self.base_charge,
            "energy_charge": self.energy_charge,
            "tdu_delivery_charge": self.tdu_delivery_charge,
            "tdu_per_kwh": self.tdu_per_kwh,
            "cancellation_fee": self.cancellation_fee,
            "renewable_pct": self.renewable_pct,
            "is_time_of_use": self.is_time_of_use,
        }

    def estimate_monthly_cost(self, monthly_kwh):
        """Estimate monthly cost for a given usage in kWh.

        Uses the energy_charge + base_charge + TDU components if available.
        Falls back to interpolating from the 500/1000/2000 tier prices.
        """
        if self.energy_charge is not None:
            energy_cost = self.energy_charge * monthly_kwh
            tdu_cost = (self.tdu_delivery_charge or 0) + (self.tdu_per_kwh or 0) * monthly_kwh
            return (self.base_charge or 0) + energy_cost + tdu_cost

        # Fallback: interpolate from tier prices (these are cents/kWh all-in)
        if monthly_kwh <= 500 and self.price_kwh_500:
            return self.price_kwh_500 * monthly_kwh / 100
        elif monthly_kwh <= 1000 and self.price_kwh_1000:
            return self.price_kwh_1000 * monthly_kwh / 100
        elif self.price_kwh_2000:
            return self.price_kwh_2000 * monthly_kwh / 100
        return None
