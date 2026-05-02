from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..analytics import run_full_analysis
from ..auth import require_role
from ..database import get_db
from ..templating import templates
from ..models import (
    Bill,
    ConsumptionAnomaly,
    InspectionRequest,
    MeterReading,
    Role,
    Subscriber,
    User,
    WaterCompany,
)

router = APIRouter(prefix="/water-company", tags=["water_company"])


def _ctx(request, user, **kw):
    return {"request": request, "user": user, "Role": Role, **kw}


def _me(db, user) -> WaterCompany:
    wc = db.execute(select(WaterCompany).where(WaterCompany.user_id == user.id)).scalar_one_or_none()
    if not wc:
        raise HTTPException(404)
    return wc


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.WATER_COMPANY))):
    wc = _me(db, user)
    subscribers = db.execute(select(Subscriber).where(Subscriber.water_company_id == wc.id)).scalars().all()
    sub_ids = [s.id for s in subscribers]

    total_m3 = 0.0
    total_amount = 0.0
    monthly: dict[str, float] = {}
    if sub_ids:
        bills = db.execute(select(Bill).where(Bill.subscriber_id.in_(sub_ids))).scalars().all()
        for b in bills:
            total_m3 += b.cubic_meters
            total_amount += b.amount
            key = b.period_start.strftime("%Y-%m")
            monthly[key] = monthly.get(key, 0.0) + b.cubic_meters
    monthly_sorted = sorted(monthly.items())[-12:]
    max_m = max((v for _, v in monthly_sorted), default=1.0)

    anomalies = db.execute(
        select(ConsumptionAnomaly)
        .where(ConsumptionAnomaly.subscriber_id.in_(sub_ids))
        .order_by(ConsumptionAnomaly.detected_at.desc())
    ).scalars().all() if sub_ids else []

    inspections = db.execute(
        select(InspectionRequest).where(InspectionRequest.subscriber_id.in_(sub_ids))
    ).scalars().all() if sub_ids else []

    return templates.TemplateResponse("water_company/dashboard.html", _ctx(
        request, user, wc=wc, subscribers=subscribers, total_m3=total_m3, total_amount=total_amount,
        monthly=monthly_sorted, max_m=max_m, anomalies=anomalies, inspections=inspections,
    ))


@router.get("/subscribers")
def subscribers_list(request: Request, db: Session = Depends(get_db),
                     user: User = Depends(require_role(Role.WATER_COMPANY))):
    wc = _me(db, user)
    subs = db.execute(select(Subscriber).where(Subscriber.water_company_id == wc.id)).scalars().all()
    rows = []
    for s in subs:
        last = db.execute(
            select(Bill).where(Bill.subscriber_id == s.id).order_by(Bill.period_start.desc())
        ).scalars().first()
        anomaly = db.execute(
            select(ConsumptionAnomaly).where(ConsumptionAnomaly.subscriber_id == s.id)
            .order_by(ConsumptionAnomaly.detected_at.desc())
        ).scalars().first()
        rows.append({"sub": s, "last": last, "anomaly": anomaly})
    return templates.TemplateResponse("water_company/subscribers.html", _ctx(request, user, wc=wc, rows=rows))


@router.post("/run-analytics")
def run_analytics(db: Session = Depends(get_db),
                  user: User = Depends(require_role(Role.WATER_COMPANY))):
    run_full_analysis(db)
    return RedirectResponse("/water-company", status_code=303)


@router.get("/upload")
def upload_form(request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.WATER_COMPANY))):
    wc = _me(db, user)
    subs = db.execute(select(Subscriber).where(Subscriber.water_company_id == wc.id)).scalars().all()
    return templates.TemplateResponse("water_company/upload.html", _ctx(request, user, wc=wc, subs=subs))


@router.post("/upload")
def upload_submit(subscriber_id: int = Form(...),
                  cubic_meters: float = Form(...),
                  db: Session = Depends(get_db),
                  user: User = Depends(require_role(Role.WATER_COMPANY))):
    wc = _me(db, user)
    sub = db.get(Subscriber, subscriber_id)
    if not sub or sub.water_company_id != wc.id:
        raise HTTPException(404)
    today = date.today().replace(day=1)
    if today.month == 12:
        period_end = today.replace(year=today.year + 1, month=1) - timedelta(days=1)
    else:
        period_end = today.replace(month=today.month + 1) - timedelta(days=1)
    db.add(MeterReading(subscriber_id=sub.id, period_start=today, period_end=period_end, cubic_meters=cubic_meters))
    db.add(Bill(subscriber_id=sub.id, period_start=today, period_end=period_end,
                cubic_meters=cubic_meters, amount=round(6.50 + cubic_meters * 1.85, 2), paid=False))
    db.commit()
    return RedirectResponse("/water-company/upload", status_code=303)
