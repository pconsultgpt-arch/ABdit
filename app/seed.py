"""Seed the database with realistic demo data.

Idempotent: drops all tables and recreates them every run so the demo always
starts in a known state.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from sqlalchemy import select

from .analytics import run_full_analysis
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import (
    Bill,
    InspectionReport,
    InspectionRequest,
    InspectionStatus,
    Installation,
    KnowledgeBaseEntry,
    MeterReading,
    Product,
    ProductCategory,
    Proposal,
    ProposalItem,
    Provider,
    Role,
    Specialist,
    Subscriber,
    TrainingProgram,
    User,
    WaterCompany,
)

random.seed(42)

PRICE_PER_M3 = 1.85  # currency units per cubic meter
FIXED_FEE = 6.50


def _make_user(db, email, full_name, role: Role) -> User:
    user = User(
        email=email,
        password_hash=hash_password("password"),
        full_name=full_name,
        role=role.value,
    )
    db.add(user)
    db.flush()
    return user


def _seasonal_factor(month: int, has_garden: bool) -> float:
    # Northern-hemisphere seasonality: more outdoor use May-Sep, much more if garden
    base = {
        1: 0.92, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.10, 6: 1.20,
        7: 1.30, 8: 1.32, 9: 1.18, 10: 1.05, 11: 0.95, 12: 0.92,
    }[month]
    if has_garden and month in (5, 6, 7, 8, 9):
        base *= 1.25
    return base


def _baseline_m3(household_size: int, has_garden: bool, has_pool: bool) -> float:
    base = 6.0 + household_size * 4.0
    if has_garden:
        base += 6.0
    if has_pool:
        base += 8.0
    return base


def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed():
    reset_database()
    db = SessionLocal()
    try:
        # ---- Admin / Abdit operators ----
        admin_user = _make_user(db, "admin@abdit.io", "Abdit Operator", Role.ADMIN)

        # ---- Water company ----
        wc_user = _make_user(db, "ops@bluecity-water.com", "Blue City Water Ops", Role.WATER_COMPANY)
        wc = WaterCompany(user_id=wc_user.id, name="Blue City Water", region="Blue City")
        db.add(wc)
        db.flush()

        # ---- Specialists ----
        specialists = []
        for i, name in enumerate(["Sara Nadir", "Omar Hayek", "Lina Ferraro"]):
            email = f"specialist{i+1}@abdit.io"
            su = _make_user(db, email, name, Role.SPECIALIST)
            sp = Specialist(
                user_id=su.id,
                certification_level="Senior" if i == 0 else "Certified",
                region="Blue City",
                rating=4.6 + 0.1 * i,
                completed_jobs=random.randint(8, 40),
            )
            db.add(sp)
            db.flush()
            specialists.append(sp)

        # ---- Providers ----
        providers_data = [
            ("AquaSmart Devices", "aquasmart@abdit.io", "Smart irrigation and metering."),
            ("EcoFit Plumbing", "ecofit@abdit.io", "Efficient faucets, showerheads, leak sensors."),
            ("HydroLoop Systems", "hydroloop@abdit.io", "Greywater recycling for homes and small estates."),
        ]
        providers: list[Provider] = []
        for company, email, desc in providers_data:
            pu = _make_user(db, email, company, Role.PROVIDER)
            p = Provider(user_id=pu.id, company_name=company, description=desc)
            db.add(p)
            db.flush()
            providers.append(p)

        # ---- Products ----
        catalog = [
            (providers[0], "AquaSmart IR-200 Irrigation Controller", ProductCategory.SMART_IRRIGATION,
             "Weather-aware controller, schedules irrigation by ET₀ and soil moisture.", 220.0, 60.0, 18.0),
            (providers[0], "AquaSmart M-Flow Smart Meter", ProductCategory.SMART_METER,
             "Realtime LoRaWAN meter with leak alerts.", 180.0, 80.0, 6.0),
            (providers[1], "EcoFit Aerator Bundle (5 taps)", ProductCategory.EFFICIENT_FAUCET,
             "Drop-in aerators reducing flow to 4 L/min without pressure loss.", 35.0, 15.0, 8.0),
            (providers[1], "EcoFit Rainshower Pro", ProductCategory.EFFICIENT_SHOWERHEAD,
             "6 L/min showerhead with thermo-sensitive trigger.", 55.0, 20.0, 10.0),
            (providers[1], "EcoFit Leak Sentinel", ProductCategory.LEAK_DETECTION,
             "Whole-home acoustic leak detector with auto-shutoff.", 290.0, 120.0, 12.0),
            (providers[2], "HydroLoop GW-1 Greywater Recycler", ProductCategory.WATER_RECYCLING,
             "Recycles shower & sink water for toilet flushing and garden use.", 1450.0, 300.0, 28.0),
        ]
        products: list[Product] = []
        for prov, name, cat, desc, price, install, savings in catalog:
            prod = Product(
                provider_id=prov.id,
                name=name,
                category=cat.value,
                description=desc,
                price=price,
                install_fee=install,
                expected_savings_pct=savings,
            )
            db.add(prod)
            db.flush()
            products.append(prod)

        # ---- Subscribers ----
        subscriber_specs = [
            # email, name, address, city, household, garden, pool, anomalous_factor (multiplier on latest month)
            ("amal@example.com", "Amal Khoury", "12 Olive Lane", "Blue City", 4, True, False, 1.85),
            ("rashid@example.com", "Rashid Saleh", "44 Cedar Way", "Blue City", 3, False, False, 1.05),
            ("nadia@example.com", "Nadia Costa", "9 Harbor Rd", "Blue City", 5, True, True, 1.55),
            ("yusuf@example.com", "Yusuf Bahar", "3 Marina Pl", "Blue City", 2, False, False, 0.95),
            ("layla@example.com", "Layla Demir", "27 Pine St", "Blue City", 6, True, False, 1.40),
            ("kareem@example.com", "Kareem Dabbagh", "5 Sunset Blvd", "Blue City", 1, False, False, 1.10),
            ("noor@example.com", "Noor El-Amin", "8 Garden Court", "Blue City", 4, True, False, 1.00),
            ("samir@example.com", "Samir Haddad", "19 Hilltop", "Blue City", 3, False, False, 1.65),
        ]

        subscribers: list[Subscriber] = []
        for i, (email, name, addr, city, hh, garden, pool, factor) in enumerate(subscriber_specs):
            su = _make_user(db, email, name, Role.SUBSCRIBER)
            sub = Subscriber(
                user_id=su.id,
                water_company_id=wc.id,
                account_number=f"BCW-{1000+i:04d}",
                address=addr,
                city=city,
                household_size=hh,
                has_garden=garden,
                has_pool=pool,
                property_type="residential",
            )
            db.add(sub)
            db.flush()
            subscribers.append(sub)

            # 18 months of monthly readings + bills
            today = date.today().replace(day=1)
            baseline = _baseline_m3(hh, garden, pool)
            for months_ago in range(18, 0, -1):
                period_start = (today - timedelta(days=30 * months_ago)).replace(day=1)
                # Approximate end-of-month
                if period_start.month == 12:
                    period_end = period_start.replace(year=period_start.year + 1, month=1) - timedelta(days=1)
                else:
                    period_end = period_start.replace(month=period_start.month + 1) - timedelta(days=1)
                month = period_start.month
                noise = random.uniform(0.92, 1.08)
                m3 = baseline * _seasonal_factor(month, garden) * noise
                if months_ago == 1:
                    m3 *= factor  # introduce anomaly on latest month
                m3 = round(m3, 1)
                amount = round(FIXED_FEE + m3 * PRICE_PER_M3, 2)

                db.add(MeterReading(
                    subscriber_id=sub.id,
                    period_start=period_start,
                    period_end=period_end,
                    cubic_meters=m3,
                ))
                db.add(Bill(
                    subscriber_id=sub.id,
                    period_start=period_start,
                    period_end=period_end,
                    cubic_meters=m3,
                    amount=amount,
                    paid=months_ago > 1,
                ))
        db.commit()

        # ---- Run analytics → generate anomalies + notifications ----
        run_full_analysis(db)

        # ---- Pre-populated inspection workflow for subscriber #1 (Amal) ----
        amal = subscribers[0]
        anomaly = db.execute(
            select(__import__("app.models", fromlist=["ConsumptionAnomaly"]).ConsumptionAnomaly)
            .where(__import__("app.models", fromlist=["ConsumptionAnomaly"]).ConsumptionAnomaly.subscriber_id == amal.id)
        ).scalars().first()

        insp = InspectionRequest(
            subscriber_id=amal.id,
            specialist_id=specialists[0].id,
            anomaly_id=anomaly.id if anomaly else None,
            status=InspectionStatus.REPORT_SUBMITTED.value,
            requested_at=datetime.utcnow() - timedelta(days=6),
            scheduled_for=datetime.utcnow() - timedelta(days=2),
            notes="Subscriber reports unusually high bill last month; suspects garden irrigation overrun.",
        )
        db.add(insp)
        db.flush()

        report = InspectionReport(
            inspection_id=insp.id,
            plumbing_findings="Two faucets dripping in kitchen and guest bath; toilet flapper sticking.",
            irrigation_findings="Drip system zone 3 stuck open at night — running ~4h longer than scheduled.",
            leakage_findings="Acoustic check confirmed continuous flow on irrigation line.",
            usage_observations="Household practices reasonable, but no awareness of irrigation overrun.",
            estimated_savings_pct=22.0,
            summary="Most savings from fixing irrigation controller + leak guard. Aerators give incremental wins.",
        )
        db.add(report)

        proposal = Proposal(inspection_id=insp.id, status="sent",
                            notes="Mix of immediate quick wins and a smart controller upgrade.")
        db.add(proposal)
        db.flush()

        for prod in [products[0], products[2], products[4]]:
            db.add(ProposalItem(
                proposal_id=proposal.id,
                product_id=prod.id,
                quantity=1,
                unit_price=prod.price,
                install_fee=prod.install_fee,
                selected=True,
            ))
        db.commit()

        # ---- One fully-completed installation (subscriber #3, Nadia) ----
        nadia = subscribers[2]
        nadia_anom = db.execute(
            select(__import__("app.models", fromlist=["ConsumptionAnomaly"]).ConsumptionAnomaly)
            .where(__import__("app.models", fromlist=["ConsumptionAnomaly"]).ConsumptionAnomaly.subscriber_id == nadia.id)
        ).scalars().first()
        insp2 = InspectionRequest(
            subscriber_id=nadia.id,
            specialist_id=specialists[1].id,
            anomaly_id=nadia_anom.id if nadia_anom else None,
            status=InspectionStatus.INSTALLED.value,
            requested_at=datetime.utcnow() - timedelta(days=45),
            scheduled_for=datetime.utcnow() - timedelta(days=40),
            notes="Pool top-up + garden irrigation high.",
        )
        db.add(insp2)
        db.flush()
        db.add(InspectionReport(
            inspection_id=insp2.id,
            plumbing_findings="No visible leaks indoors.",
            irrigation_findings="Sprinkler zone overlap; controller not weather-aware.",
            leakage_findings="Pool top-up valve cycling more than expected.",
            usage_observations="Family of 5; pool used heavily in summer.",
            estimated_savings_pct=20.0,
            summary="Smart irrigation controller + leak sentinel recommended.",
        ))
        prop2 = Proposal(inspection_id=insp2.id, status="accepted",
                         accepted_at=datetime.utcnow() - timedelta(days=35),
                         notes="Accepted full bundle.")
        db.add(prop2)
        db.flush()
        for prod in [products[0], products[4]]:
            db.add(ProposalItem(
                proposal_id=prop2.id,
                product_id=prod.id,
                quantity=1,
                unit_price=prod.price,
                install_fee=prod.install_fee,
                selected=True,
            ))
        db.add(Installation(
            proposal_id=prop2.id,
            installed_at=datetime.utcnow() - timedelta(days=30),
            status="verified",
            actual_savings_pct=23.5,
            feedback="Subscriber happy. Bills already showing reduction in last cycle.",
        ))
        db.commit()

        # ---- Knowledge base ----
        kb_entries = [
            KnowledgeBaseEntry(
                title="Weather-aware irrigation controllers",
                category="irrigation",
                content="Replacing time-based controllers with ET-based weather-aware controllers "
                        "typically reduces outdoor consumption by 15-25%, especially in arid climates.",
                region="Blue City",
                expected_savings_pct=18.0,
                cases_count=12,
            ),
            KnowledgeBaseEntry(
                title="Faucet aerators in residential settings",
                category="indoor",
                content="Low-flow aerators (4-6 L/min) cut faucet water use by 30-50% with no perceived "
                        "loss of pressure. Best ROI of any intervention; payback < 6 months.",
                region="",
                expected_savings_pct=8.0,
                cases_count=27,
            ),
            KnowledgeBaseEntry(
                title="Continuous-flow leakage in irrigation systems",
                category="leakage",
                content="Stuck solenoid valves and split drip lines cause invisible continuous flow. "
                        "Acoustic and flow-baseline detection identify them quickly. ~22% mean savings "
                        "post-fix in observed cases.",
                region="Blue City",
                expected_savings_pct=22.0,
                cases_count=9,
            ),
            KnowledgeBaseEntry(
                title="Greywater recycling for households with gardens",
                category="recycling",
                content="Greywater systems recycle shower & sink water for toilet flushing and "
                        "irrigation, cutting potable use 25-35% in suitable households.",
                region="",
                expected_savings_pct=28.0,
                cases_count=4,
            ),
        ]
        for e in kb_entries:
            db.add(e)

        # ---- Training programs ----
        programs = [
            TrainingProgram(
                institution="Blue City Polytechnic",
                name="Certified Water Efficiency Auditor",
                duration_weeks=6,
                description="Field auditing, leak detection, hydraulic basics, customer-facing reporting.",
                certified_count=42,
            ),
            TrainingProgram(
                institution="Regional Hydro Institute",
                name="Smart Irrigation Specialist",
                duration_weeks=4,
                description="Smart controllers, ET₀, soil moisture sensors, hydrozoning.",
                certified_count=18,
            ),
        ]
        for tp in programs:
            db.add(tp)

        db.commit()
        print("Seed complete.")
        print("  Logins (password = 'password'):")
        print("    admin@abdit.io                (Abdit operator)")
        print("    ops@bluecity-water.com        (Water company)")
        print("    amal@example.com              (Subscriber w/ open proposal)")
        print("    nadia@example.com             (Subscriber w/ verified install)")
        print("    samir@example.com             (Subscriber w/ open notification)")
        print("    specialist1@abdit.io          (Specialist)")
        print("    aquasmart@abdit.io            (Provider)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
