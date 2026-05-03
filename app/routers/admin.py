from datetime import datetime

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
    Installation,
    KnowledgeBaseEntry,
    Product,
    Proposal,
    Provider,
    Role,
    Specialist,
    Subscriber,
    TrainingProgram,
    User,
    WaterCompany,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _ctx(request, user, **kw):
    return {"request": request, "user": user, "Role": Role, **kw}


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.ADMIN))):
    counts = {
        "subscribers": db.scalar(select(func.count(Subscriber.id))),
        "specialists": db.scalar(select(func.count(Specialist.id))),
        "providers": db.scalar(select(func.count(Provider.id))),
        "water_companies": db.scalar(select(func.count(WaterCompany.id))),
        "products": db.scalar(select(func.count(Product.id))),
        "anomalies": db.scalar(select(func.count(ConsumptionAnomaly.id))),
        "inspections": db.scalar(select(func.count(InspectionRequest.id))),
        "proposals": db.scalar(select(func.count(Proposal.id))),
        "kb_entries": db.scalar(select(func.count(KnowledgeBaseEntry.id))),
    }
    pipeline = {}
    for status, in db.execute(select(InspectionRequest.status)).all():
        pipeline[status] = pipeline.get(status, 0) + 1
    installations = db.execute(select(Installation)).scalars().all()
    avg_savings = (
        sum(i.actual_savings_pct for i in installations if i.actual_savings_pct is not None)
        / max(1, sum(1 for i in installations if i.actual_savings_pct is not None))
    )
    return templates.TemplateResponse("admin/dashboard.html", _ctx(
        request, user, counts=counts, pipeline=pipeline, avg_savings=avg_savings,
        installations=installations,
    ))


@router.post("/run-analytics")
def run_analytics(db: Session = Depends(get_db),
                  user: User = Depends(require_role(Role.ADMIN))):
    run_full_analysis(db)
    return RedirectResponse("/admin", status_code=303)


@router.get("/knowledge-base")
def kb(request: Request, db: Session = Depends(get_db),
       user: User = Depends(require_role(Role.ADMIN))):
    items = db.execute(select(KnowledgeBaseEntry)).scalars().all()
    return templates.TemplateResponse("admin/knowledge_base.html", _ctx(request, user, items=items))


@router.post("/knowledge-base")
def add_kb(title: str = Form(...), category: str = Form(...), content: str = Form(...),
           region: str = Form(""), expected_savings_pct: float = Form(0.0),
           db: Session = Depends(get_db),
           user: User = Depends(require_role(Role.ADMIN))):
    db.add(KnowledgeBaseEntry(
        title=title, category=category, content=content,
        region=region, expected_savings_pct=expected_savings_pct, cases_count=0,
    ))
    db.commit()
    return RedirectResponse("/admin/knowledge-base", status_code=303)


@router.get("/training")
def training(request: Request, db: Session = Depends(get_db),
             user: User = Depends(require_role(Role.ADMIN))):
    programs = db.execute(select(TrainingProgram)).scalars().all()
    specialists = db.execute(select(Specialist)).scalars().all()
    return templates.TemplateResponse("admin/training.html", _ctx(request, user, programs=programs, specialists=specialists))


@router.get("/users")
def users(request: Request, db: Session = Depends(get_db),
          user: User = Depends(require_role(Role.ADMIN))):
    all_users = db.execute(select(User)).scalars().all()
    return templates.TemplateResponse("admin/users.html", _ctx(request, user, all_users=all_users))
