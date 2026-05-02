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
        admin_user = _make_user(db, "admin@abdit.io", "اپراتور آبدیت", Role.ADMIN)

        # ---- Water company ----
        wc_user = _make_user(db, "ops@bluecity-water.com", "اپراتور شرکت آب شهر آبی", Role.WATER_COMPANY)
        wc = WaterCompany(user_id=wc_user.id, name="آب شهر آبی", region="شهر آبی")
        db.add(wc)
        db.flush()

        # ---- Specialists ----
        specialists = []
        for i, name in enumerate(["مریم رضایی", "آرش محمدی", "نگار حسینی"]):
            email = f"specialist{i+1}@abdit.io"
            su = _make_user(db, email, name, Role.SPECIALIST)
            sp = Specialist(
                user_id=su.id,
                certification_level="ارشد" if i == 0 else "دارای گواهی",
                region="شهر آبی",
                rating=4.6 + 0.1 * i,
                completed_jobs=random.randint(8, 40),
            )
            db.add(sp)
            db.flush()
            specialists.append(sp)

        # ---- Providers ----
        providers_data = [
            ("آکواسمارت", "aquasmart@abdit.io", "تجهیزات آبیاری هوشمند و کنتورهای پیشرفته."),
            ("اکوفیت", "ecofit@abdit.io", "شیرآلات، دوش‌ها و حسگرهای نشت‌یاب کم‌مصرف."),
            ("هیدرولوپ", "hydroloop@abdit.io", "سامانه‌های بازچرخانی آب خاکستری برای منازل و مجموعه‌های کوچک."),
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
            (providers[0], "کنترلر آبیاری هوشمند آکواسمارت IR-200", ProductCategory.SMART_IRRIGATION,
             "کنترلر هوشمند آبیاری مبتنی بر تبخیر و رطوبت خاک.", 220.0, 60.0, 18.0),
            (providers[0], "کنتور هوشمند آکواسمارت M-Flow", ProductCategory.SMART_METER,
             "کنتور آب لحظه‌ای با ارتباط LoRaWAN و هشدار نشت.", 180.0, 80.0, 6.0),
            (providers[1], "بستهٔ هوادهندهٔ شیرآلات اکوفیت (۵ شیر)", ProductCategory.EFFICIENT_FAUCET,
             "هوادهنده‌های شیر برای کاهش مصرف به ۴ لیتر در دقیقه بدون افت فشار.", 35.0, 15.0, 8.0),
            (providers[1], "دوش کم‌مصرف اکوفیت Rainshower Pro", ProductCategory.EFFICIENT_SHOWERHEAD,
             "دوش ۶ لیتر در دقیقه با شیر خاموش‌کن حرارتی.", 55.0, 20.0, 10.0),
            (providers[1], "نشت‌یاب صوتی اکوفیت Leak Sentinel", ProductCategory.LEAK_DETECTION,
             "نشت‌یاب صوتی برای کل منزل با قابلیت قطع خودکار جریان.", 290.0, 120.0, 12.0),
            (providers[2], "بازچرخانگر آب خاکستری هیدرولوپ GW-1", ProductCategory.WATER_RECYCLING,
             "بازچرخانی آب دوش و سینک برای استفاده در فلاش و باغچه.", 1450.0, 300.0, 28.0),
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
            ("amal@example.com", "امیر کریمی", "خیابان زیتون، پلاک ۱۲", "شهر آبی", 4, True, False, 1.85),
            ("rashid@example.com", "رشید صالحی", "خیابان سرو، پلاک ۴۴", "شهر آبی", 3, False, False, 1.05),
            ("nadia@example.com", "ندا خوشدل", "خیابان بندر، پلاک ۹", "شهر آبی", 5, True, True, 1.55),
            ("yusuf@example.com", "یوسف بحری", "میدان مارینا، پلاک ۳", "شهر آبی", 2, False, False, 0.95),
            ("layla@example.com", "لیلا کاظمی", "خیابان کاج، پلاک ۲۷", "شهر آبی", 6, True, False, 1.40),
            ("kareem@example.com", "کریم دباغ", "بلوار غروب، پلاک ۵", "شهر آبی", 1, False, False, 1.10),
            ("noor@example.com", "نور احمدی", "کوچهٔ باغ، پلاک ۸", "شهر آبی", 4, True, False, 1.00),
            ("samir@example.com", "سمیر حداد", "خیابان تپه، پلاک ۱۹", "شهر آبی", 3, False, False, 1.65),
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
            notes="مشترک گزارش می‌دهد که صورت‌حساب ماه گذشته به‌طور غیرعادی بالا بوده؛ احتمال اضافه‌مصرف سامانهٔ آبیاری باغچه را مطرح کرده است.",
        )
        db.add(insp)
        db.flush()

        report = InspectionReport(
            inspection_id=insp.id,
            plumbing_findings="دو شیر چکه‌دار در آشپزخانه و سرویس مهمان؛ گیرکردن فلپ توالت.",
            irrigation_findings="منطقهٔ ۳ سامانهٔ قطره‌ای شب‌ها در حالت باز گیر کرده — حدود ۴ ساعت بیش از برنامه روشن می‌ماند.",
            leakage_findings="بررسی صوتی، جریان پیوسته روی خط آبیاری را تأیید کرد.",
            usage_observations="عادات مصرف خانوار منطقی است، ولی از اضافه‌مصرف سامانهٔ آبیاری اطلاع نداشتند.",
            estimated_savings_pct=22.0,
            summary="بیشترین صرفه‌جویی از اصلاح کنترلر آبیاری و نصب نشت‌یاب حاصل می‌شود؛ هوادهنده‌ها صرفه‌جویی تکمیلی می‌دهند.",
        )
        db.add(report)

        proposal = Proposal(inspection_id=insp.id, status="sent",
                            notes="ترکیبی از راهکارهای سریع و ارتقای کنترلر هوشمند آبیاری.")
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
            notes="آبگیری استخر و آبیاری باغچه بیش از حد انتظار است.",
        )
        db.add(insp2)
        db.flush()
        db.add(InspectionReport(
            inspection_id=insp2.id,
            plumbing_findings="نشت آشکاری در داخل ساختمان مشاهده نشد.",
            irrigation_findings="هم‌پوشانی مناطق آبپاش‌ها؛ کنترلر فاقد قابلیت تشخیص شرایط جوی.",
            leakage_findings="شیر آبگیری استخر بیش از حد معمول وارد چرخهٔ شارژ می‌شود.",
            usage_observations="خانوادهٔ ۵ نفره؛ استخر در تابستان استفادهٔ زیاد دارد.",
            estimated_savings_pct=20.0,
            summary="نصب کنترلر هوشمند آبیاری و نشت‌یاب توصیه می‌شود.",
        ))
        prop2 = Proposal(inspection_id=insp2.id, status="accepted",
                         accepted_at=datetime.utcnow() - timedelta(days=35),
                         notes="کل بسته پذیرفته شد.")
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
            feedback="مشترک رضایت دارد. کاهش مصرف در صورت‌حساب دورهٔ اخیر مشاهده شده است.",
        ))
        db.commit()

        # ---- Knowledge base ----
        kb_entries = [
            KnowledgeBaseEntry(
                title="کنترلرهای آبیاری مبتنی بر شرایط جوی",
                category="آبیاری",
                content="جایگزینی کنترلرهای زمان‌بنیاد با کنترلرهای مبتنی بر تبخیر و شرایط جوی، "
                        "مصرف فضای سبز را به‌طور معمول ۱۵ تا ۲۵ درصد کاهش می‌دهد، به‌ویژه در اقلیم‌های خشک.",
                region="شهر آبی",
                expected_savings_pct=18.0,
                cases_count=12,
            ),
            KnowledgeBaseEntry(
                title="هوادهنده‌های شیرآلات در منازل",
                category="مصرف داخلی",
                content="هوادهنده‌های کم‌مصرف (۴ تا ۶ لیتر در دقیقه) مصرف شیرآلات را ۳۰ تا ۵۰ درصد کاهش "
                        "می‌دهند بدون آن‌که افت فشار محسوس باشد. بهترین بازگشت سرمایه در میان "
                        "اقدامات بهینه‌مصرف؛ بازگشت سرمایه کمتر از ۶ ماه.",
                region="",
                expected_savings_pct=8.0,
                cases_count=27,
            ),
            KnowledgeBaseEntry(
                title="نشت پیوسته در سامانه‌های آبیاری",
                category="نشت",
                content="گیرکردن شیرهای برقی و پارگی خطوط قطره‌ای موجب جریان پیوستهٔ نامرئی می‌شود. "
                        "تشخیص صوتی و پایش جریان مبنا این موارد را به‌سرعت شناسایی می‌کند. "
                        "میانگین صرفه‌جویی پس از اصلاح حدود ۲۲ درصد بوده است.",
                region="شهر آبی",
                expected_savings_pct=22.0,
                cases_count=9,
            ),
            KnowledgeBaseEntry(
                title="بازچرخانی آب خاکستری برای منازل دارای باغچه",
                category="بازچرخانی",
                content="سامانه‌های آب خاکستری، آب دوش و سینک را برای استفاده در فلاش توالت و "
                        "آبیاری بازچرخانی می‌کنند و مصرف آب آشامیدنی را در منازل مناسب ۲۵ تا ۳۵ درصد کاهش می‌دهند.",
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
                institution="پلی‌تکنیک شهر آبی",
                name="ممیز رسمی بهینه‌مصرف آب",
                duration_weeks=6,
                description="بازرسی میدانی، نشت‌یابی، مبانی هیدرولیک و گزارش‌نویسی برای مشترکان.",
                certified_count=42,
            ),
            TrainingProgram(
                institution="مؤسسهٔ منطقه‌ای آب",
                name="متخصص آبیاری هوشمند",
                duration_weeks=4,
                description="کنترلرهای هوشمند، تبخیر مرجع، حسگرهای رطوبت خاک و منطقه‌بندی آبیاری.",
                certified_count=18,
            ),
        ]
        for tp in programs:
            db.add(tp)

        db.commit()
        print("ایجاد دادهٔ نمایشی به پایان رسید.")
        print("  حساب‌های نمایشی (رمز عبور = 'password'):")
        print("    admin@abdit.io                (اپراتور آبدیت)")
        print("    ops@bluecity-water.com        (شرکت آب)")
        print("    amal@example.com              (مشترک با پیش‌فاکتور باز)")
        print("    nadia@example.com             (مشترک با نصب تأییدشده)")
        print("    samir@example.com             (مشترک با اعلان جدید)")
        print("    specialist1@abdit.io          (متخصص)")
        print("    aquasmart@abdit.io            (تأمین‌کننده)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
