from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import (
    Product,
    ProductCategory,
    ProposalItem,
    Provider,
    Role,
    User,
)

router = APIRouter(prefix="/provider", tags=["provider"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
templates.env.globals["now"] = datetime.utcnow


def _ctx(request, user, **kw):
    return {"request": request, "user": user, "Role": Role, "categories": [c.value for c in ProductCategory], **kw}


def _me(db, user) -> Provider:
    p = db.execute(select(Provider).where(Provider.user_id == user.id)).scalar_one_or_none()
    if not p:
        raise HTTPException(404)
    return p


@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_role(Role.PROVIDER))):
    me = _me(db, user)
    products = db.execute(select(Product).where(Product.provider_id == me.id)).scalars().all()
    # Count proposal items per product
    stats = []
    for p in products:
        count = db.execute(
            select(ProposalItem).where(ProposalItem.product_id == p.id)
        ).scalars().all()
        accepted = sum(1 for i in count if i.proposal.status == "accepted")
        stats.append({"product": p, "in_proposals": len(count), "accepted": accepted})
    return templates.TemplateResponse("provider/dashboard.html", _ctx(request, user, me=me, stats=stats))


@router.get("/products/new")
def new_product(request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.PROVIDER))):
    me = _me(db, user)
    return templates.TemplateResponse("provider/product_form.html", _ctx(request, user, me=me, p=None))


@router.post("/products/new")
def create_product(name: str = Form(...), category: str = Form(...), description: str = Form(""),
                   price: float = Form(...), install_fee: float = Form(0.0),
                   expected_savings_pct: float = Form(0.0),
                   db: Session = Depends(get_db),
                   user: User = Depends(require_role(Role.PROVIDER))):
    me = _me(db, user)
    db.add(Product(provider_id=me.id, name=name, category=category, description=description,
                   price=price, install_fee=install_fee, expected_savings_pct=expected_savings_pct))
    db.commit()
    return RedirectResponse("/provider", status_code=303)


@router.get("/products/{pid}")
def edit_product(pid: int, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_role(Role.PROVIDER))):
    me = _me(db, user)
    p = db.get(Product, pid)
    if not p or p.provider_id != me.id:
        raise HTTPException(404)
    return templates.TemplateResponse("provider/product_form.html", _ctx(request, user, me=me, p=p))


@router.post("/products/{pid}")
def update_product(pid: int,
                   name: str = Form(...), category: str = Form(...), description: str = Form(""),
                   price: float = Form(...), install_fee: float = Form(0.0),
                   expected_savings_pct: float = Form(0.0),
                   active: str = Form("on"),
                   db: Session = Depends(get_db),
                   user: User = Depends(require_role(Role.PROVIDER))):
    me = _me(db, user)
    p = db.get(Product, pid)
    if not p or p.provider_id != me.id:
        raise HTTPException(404)
    p.name = name
    p.category = category
    p.description = description
    p.price = price
    p.install_fee = install_fee
    p.expected_savings_pct = expected_savings_pct
    p.active = active == "on"
    db.commit()
    return RedirectResponse("/provider", status_code=303)
