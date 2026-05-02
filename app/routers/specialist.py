from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..templating import templates
from ..models import (
    InspectionReport,
    InspectionRequest,
    InspectionStatus,
    Installation,
    Product,
    Proposal,
    ProposalItem,
    Role,
    Specialist,
    User,
)

router = APIRouter(prefix="/specialist", tags=["specialist"])


def _ctx(request, user, **kw):
    return {"request": request, "user": user, "Role": Role, **kw}


def _me(db: Session, user: User) -> Specialist:
    sp = db.execute(select(Specialist).where(Specialist.user_id == user.id)).scalar_one_or_none()
    if not sp:
        raise HTTPException(404)
    return sp


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    open_requests = db.execute(
        select(InspectionRequest).where(InspectionRequest.specialist_id == None,
                                        InspectionRequest.status == InspectionStatus.REQUESTED.value)
    ).scalars().all()
    my_active = db.execute(
        select(InspectionRequest).where(
            InspectionRequest.specialist_id == sp.id,
            InspectionRequest.status.in_([
                InspectionStatus.ASSIGNED.value,
                InspectionStatus.REPORT_SUBMITTED.value,
                InspectionStatus.PROPOSAL_SENT.value,
                InspectionStatus.ACCEPTED.value,
                InspectionStatus.INSTALLED.value,
            ])
        )
    ).scalars().all()
    history = db.execute(
        select(InspectionRequest).where(
            InspectionRequest.specialist_id == sp.id,
            InspectionRequest.status.in_([InspectionStatus.COMPLETED.value, InspectionStatus.DECLINED.value])
        )
    ).scalars().all()
    return templates.TemplateResponse("specialist/dashboard.html", _ctx(
        request, user, sp=sp, open_requests=open_requests, my_active=my_active, history=history,
    ))


@router.post("/inspections/{iid}/claim")
def claim(iid: int, db: Session = Depends(get_db),
          user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp:
        raise HTTPException(404)
    insp.specialist_id = sp.id
    insp.status = InspectionStatus.ASSIGNED.value
    insp.scheduled_for = datetime.utcnow()
    db.commit()
    return RedirectResponse(f"/specialist/inspections/{iid}", status_code=303)


@router.get("/inspections/{iid}")
def inspection_detail(iid: int, request: Request, db: Session = Depends(get_db),
                      user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp or (insp.specialist_id and insp.specialist_id != sp.id):
        raise HTTPException(404)
    products = db.execute(select(Product).where(Product.active == True)).scalars().all()
    return templates.TemplateResponse("specialist/inspection_detail.html", _ctx(
        request, user, sp=sp, insp=insp, products=products,
    ))


@router.post("/inspections/{iid}/report")
def submit_report(iid: int, request: Request,
                  plumbing: str = Form(""), irrigation: str = Form(""),
                  leakage: str = Form(""), usage: str = Form(""),
                  estimated_savings_pct: float = Form(0.0),
                  summary: str = Form(""),
                  db: Session = Depends(get_db),
                  user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp or insp.specialist_id != sp.id:
        raise HTTPException(404)
    if insp.report:
        report = insp.report
    else:
        report = InspectionReport(inspection_id=insp.id)
        db.add(report)
    report.plumbing_findings = plumbing
    report.irrigation_findings = irrigation
    report.leakage_findings = leakage
    report.usage_observations = usage
    report.estimated_savings_pct = estimated_savings_pct
    report.summary = summary
    report.submitted_at = datetime.utcnow()
    insp.status = InspectionStatus.REPORT_SUBMITTED.value
    db.commit()
    return RedirectResponse(f"/specialist/inspections/{iid}", status_code=303)


@router.post("/inspections/{iid}/proposal")
def submit_proposal(iid: int,
                    notes: str = Form(""),
                    product_ids: list[int] = Form(default=[]),
                    db: Session = Depends(get_db),
                    user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp or insp.specialist_id != sp.id:
        raise HTTPException(404)
    proposal = insp.proposal or Proposal(inspection_id=insp.id)
    proposal.notes = notes
    proposal.status = "sent"
    if not insp.proposal:
        db.add(proposal)
        db.flush()
    # Replace items
    for old in list(proposal.items):
        db.delete(old)
    db.flush()
    for pid in product_ids:
        prod = db.get(Product, pid)
        if not prod:
            continue
        db.add(ProposalItem(
            proposal_id=proposal.id,
            product_id=prod.id,
            quantity=1,
            unit_price=prod.price,
            install_fee=prod.install_fee,
            selected=True,
        ))
    insp.status = InspectionStatus.PROPOSAL_SENT.value
    db.commit()
    return RedirectResponse(f"/specialist/inspections/{iid}", status_code=303)


@router.post("/inspections/{iid}/install")
def mark_installed(iid: int,
                   actual_savings_pct: float = Form(0.0),
                   feedback: str = Form(""),
                   db: Session = Depends(get_db),
                   user: User = Depends(require_role(Role.SPECIALIST))):
    sp = _me(db, user)
    insp = db.get(InspectionRequest, iid)
    if not insp or insp.specialist_id != sp.id or not insp.proposal:
        raise HTTPException(404)
    install = insp.proposal.installation or Installation(proposal_id=insp.proposal.id)
    install.installed_at = datetime.utcnow()
    install.status = "verified"
    install.actual_savings_pct = actual_savings_pct
    install.feedback = feedback
    if not insp.proposal.installation:
        db.add(install)
    insp.status = InspectionStatus.COMPLETED.value
    sp.completed_jobs += 1
    db.commit()
    return RedirectResponse(f"/specialist/inspections/{iid}", status_code=303)
