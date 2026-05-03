from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import current_user, verify_password
from .database import Base, engine, get_db
from .models import Role, User
from .routers import admin, provider, specialist, subscriber, water_company
from .templating import templates

BASE_DIR = Path(__file__).resolve().parent

Base.metadata.create_all(bind=engine)

app = FastAPI(title="آبدیت – سامانهٔ هوشمند بهینه‌سازی مصرف آب")
app.add_middleware(SessionMiddleware, secret_key="abdit-demo-secret-change-me")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def role_home(role: str) -> str:
    return {
        Role.SUBSCRIBER.value: "/subscriber",
        Role.SPECIALIST.value: "/specialist",
        Role.WATER_COMPANY.value: "/water-company",
        Role.PROVIDER.value: "/provider",
        Role.ADMIN.value: "/admin",
    }.get(role, "/")


def render(request: Request, template: str, db: Session, **ctx):
    user = current_user(request, db)
    return templates.TemplateResponse(
        template,
        {"request": request, "user": user, "Role": Role, **ctx},
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user:
        return RedirectResponse(role_home(user.role), status_code=303)
    return render(request, "landing.html", db)


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, db: Session = Depends(get_db), error: str = ""):
    return render(request, "login.html", db, error=error)


@app.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                 db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=نام+کاربری+یا+رمز+عبور+اشتباه+است", status_code=303)
    request.session["user_id"] = user.id
    return RedirectResponse(role_home(user.role), status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


app.include_router(subscriber.router)
app.include_router(specialist.router)
app.include_router(water_company.router)
app.include_router(provider.router)
app.include_router(admin.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return RedirectResponse("/login", status_code=303)
    if exc.status_code == 303 and "Location" in (exc.headers or {}):
        return RedirectResponse(exc.headers["Location"], status_code=303)
    return HTMLResponse(f"<h1>{exc.status_code}</h1><p>{exc.detail}</p>", status_code=exc.status_code)
