from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import Role, User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user


def require_role(*roles: Role):
    role_values = {r.value for r in roles}

    def dependency(request: Request, db: Session = Depends(get_db)) -> User:
        user = current_user(request, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        if user.role not in role_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency
