from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analytics import estimate_savings
from ..auth import require_role
from ..database import get_db
from ..templating import templates
from ..models import (
    Bill,
    ConsumptionAnomaly,
    InspectionReport,
    InspectionRequest,
    InspectionStatus,
    Installation,
    MeterReading,
    Notification,
    Product,
    Proposal,
    ProposalItem,
    Role,
    Subscriber,
    User,
)

router = APIRouter(prefix="/subscriber", tags=["subscriber"])


def _ctx(request, user, **kw):
    return {"request": request, "user": user, "Role": Role, **kw}


def _get_subscriber(db: Session, user: User) -> Subscriber:
    sub = db.execute(select(Subscriber).where(Subscriber.user_id == user.id)).scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Subscriber profile not found")
    return sub


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    bills = db.execute(
        select(Bill).where(Bill.subscriber_id == sub.id).order_by(Bill.period_start.asc())
    ).scalars().all()
    notifications = db.execute(
        select(Notification).where(Notification.subscriber_id == sub.id, Notification.read == False)
    ).scalars().all()
    inspections = db.execute(
        select(InspectionRequest).where(InspectionRequest.subscriber_id == sub.id)
    ).scalars().all()
    anomalies = db.execute(
        select(ConsumptionAnomaly).where(ConsumptionAnomaly.subscriber_id == sub.id)
    ).scalars().all()

    last_12 = bills[-12:] if len(bills) >= 12 else bills
    total_m3 = sum(b.cubic_meters for b in last_12)
    total_amount = sum(b.amount for b in last_12)
    latest = bills[-1] if bills else None
    prev = bills[-2] if len(bills) > 1 else None
    delta_pct = None
    if latest and prev and prev.cubic_meters:
        delta_pct = (latest.cubic_meters - prev.cubic_meters) / prev.cubic_meters * 100

    chart_bills = bills[-12:]
    max_m3 = max((b.cubic_meters for b in chart_bills), default=1.0)

    return templates.TemplateResponse("subscriber/dashboard.html", _ctx(
        request, user,
        sub=sub,
        bills=bills,
        notifications=notifications,
        inspections=inspections,
        anomalies=anomalies,
        total_m3=total_m3,
        total_amount=total_amount,
        latest=latest,
        delta_pct=delta_pct,
        chart_bills=chart_bills,
        max_m3=max_m3,
    ))


@router.get("/consumption")
def consumption(request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    readings = db.execute(
        select(MeterReading).where(MeterReading.subscriber_id == sub.id).order_by(MeterReading.period_start.asc())
    ).scalars().all()
    bills = db.execute(
        select(Bill).where(Bill.subscriber_id == sub.id).order_by(Bill.period_start.asc())
    ).scalars().all()
    chart = readings[-12:]
    max_m3 = max((r.cubic_meters for r in chart), default=1.0)
    avg = sum(r.cubic_meters for r in readings) / len(readings) if readings else 0
    return templates.TemplateResponse("subscriber/consumption.html", _ctx(
        request, user, sub=sub, readings=readings, bills=bills, chart=chart, max_m3=max_m3, avg=avg,
    ))


@router.get("/notifications")
def notifications_list(request: Request, db: Session = Depends(get_db),
                       user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    items = db.execute(
        select(Notification).where(Notification.subscriber_id == sub.id).order_by(Notification.created_at.desc())
    ).scalars().all()
    return templates.TemplateResponse("subscriber/notifications.html", _ctx(request, user, sub=sub, items=items))


@router.post("/notifications/{nid}/read")
def mark_notification_read(nid: int, db: Session = Depends(get_db),
                           user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    n = db.get(Notification, nid)
    if not n or n.subscriber_id != sub.id:
        raise HTTPException(404)
    n.read = True
    db.commit()
    return RedirectResponse("/subscriber/notifications", status_code=303)


@router.post("/inspections/request")
def request_inspection(request: Request, anomaly_id: int | None = Form(None),
                       notes: str = Form(""), db: Session = Depends(get_db),
                       user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    insp = InspectionRequest(
        subscriber_id=sub.id,
        anomaly_id=anomaly_id,
        notes=notes,
        status=InspectionStatus.REQUESTED.value,
    )
    db.add(insp)
    db.commit()
    return RedirectResponse("/subscriber/inspections", status_code=303)


@router.get("/inspections")
def inspections_list(request: Request, db: Session = Depends(get_db),
                     user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    items = db.execute(
        select(InspectionRequest)
        .where(InspectionRequest.subscriber_id == sub.id)
        .order_by(InspectionRequest.requested_at.desc())
    ).scalars().all()
    return templates.TemplateResponse("subscriber/inspections.html", _ctx(request, user, sub=sub, items=items))


@router.get("/inspections/{iid}")
def inspection_detail(iid: int, request: Request, db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp or insp.subscriber_id != sub.id:
        raise HTTPException(404)
    bills = db.execute(
        select(Bill).where(Bill.subscriber_id == sub.id).order_by(Bill.period_start.asc())
    ).scalars().all()
    savings = None
    if insp.report:
        savings = estimate_savings(bills, insp.report.estimated_savings_pct)
    proposal_total = 0.0
    if insp.proposal:
        proposal_total = sum(
            (i.unit_price + i.install_fee) * i.quantity
            for i in insp.proposal.items if i.selected
        )
    return templates.TemplateResponse("subscriber/inspection_detail.html", _ctx(
        request, user, sub=sub, insp=insp, savings=savings, proposal_total=proposal_total,
    ))


@router.post("/proposals/{pid}/respond")
def respond_proposal(pid: int, decision: str = Form(...),
                     selected_items: list[int] | None = Form(default=None),
                     db: Session = Depends(get_db),
                     user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    proposal = db.get(Proposal, pid)
    if not proposal or proposal.inspection.subscriber_id != sub.id:
        raise HTTPException(404)
    if decision == "accept":
        # Update item selection
        chosen = set(selected_items or [])
        for item in proposal.items:
            item.selected = item.id in chosen if chosen else item.selected
        proposal.status = "accepted"
        proposal.accepted_at = datetime.utcnow()
        proposal.inspection.status = InspectionStatus.ACCEPTED.value
        # Create installation
        if not proposal.installation:
            db.add(Installation(proposal_id=proposal.id, status="scheduled"))
    else:
        proposal.status = "declined"
        proposal.inspection.status = InspectionStatus.DECLINED.value
    db.commit()
    return RedirectResponse(f"/subscriber/inspections/{proposal.inspection_id}", status_code=303)


@router.get("/marketplace")
def marketplace(request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.SUBSCRIBER))):
    sub = _get_subscriber(db, user)
    products = db.execute(select(Product).where(Product.active == True)).scalars().all()
    return templates.TemplateResponse("subscriber/marketplace.html", _ctx(request, user, sub=sub, products=products))
