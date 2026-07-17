"""
auth.py - Authentication routes: register, login, current user, password reset.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from . import db, ratelimit
from .deps import get_current_user
from .schemas import (ForgotResetRequest, LoginRequest, RegisterRequest,
                      TokenResponse, UserOut)
from .security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    ok, msg = db.create_user(req.username, req.password, req.security_q, req.security_a)
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, msg)
    user = db.get_user_by_username(req.username)
    return UserOut(id=user["id"], username=user["username"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    key = req.username.strip().lower()
    locked = ratelimit.seconds_locked(key)
    if locked:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Demasiados intentos. Prueba de nuevo en {locked // 60 + 1} min.",
        )
    user = db.authenticate(req.username, req.password)
    if not user:
        ratelimit.record_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password.")
    ratelimit.reset(key)
    token = create_access_token(user["id"])
    return TokenResponse(access_token=token, user=UserOut(**user))


@router.get("/me", response_model=UserOut)
def me(current=Depends(get_current_user)):
    return UserOut(id=current["id"], username=current["username"])


@router.get("/security-question")
def security_question(username: str):
    q = db.get_security_question(username)
    return {"security_q": q or ""}


@router.post("/reset-password")
def reset_password(req: ForgotResetRequest):
    ok, msg = db.reset_password(req.username, req.answer, req.new_password)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)
    return {"detail": msg}
