"""
CPIS V1 — Authentication API endpoints.

Endpoints:
  POST /api/v1/auth/login   — authenticate and receive a JWT token
  GET  /api/v1/auth/me      — return current user info (requires auth)
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.database import get_db
from app.models.user import Role, User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Schemas ────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """Current user info response."""

    id: str
    username: str
    email: str | None = None
    is_active: bool
    roles: list[str]


# ── In-memory rate limiter (simple sliding-window) ────────────────

_login_attempts: dict[str, list[float]] = {}
_LOGIN_RATE_LIMIT = 5       # max attempts
_LOGIN_RATE_WINDOW = 60     # seconds


def _check_login_rate(ip: str) -> None:
    """Raise 429 if the client has exceeded the login rate limit."""
    now = time.monotonic()
    window_start = now - _LOGIN_RATE_WINDOW

    # Prune old entries
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if t > window_start]

    if len(attempts) >= _LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {_LOGIN_RATE_WINDOW} seconds.",
        )

    attempts.append(now)
    _login_attempts[ip] = attempts


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """Authenticate with username + password, receive a JWT access token."""
    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate(client_ip)

    # Fetch user
    result = await db.execute(
        select(User)
        .where(User.username == body.username)
        .options(selectinload(User.roles)),
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is deactivated",
        )

    # Create token
    token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
    )
    return LoginResponse(access_token=token)


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Return information about the currently authenticated user."""
    return UserInfo(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=[r.name for r in current_user.roles],
    )


# ── Utility endpoint (optional, for seeding) ────────────────────────


class CreateUserRequest(BaseModel):
    """Request body for creating a new user (admin only)."""

    username: str = Field(..., min_length=2, max_length=128)
    password: str = Field(..., min_length=8)
    email: str | None = Field(None, max_length=255)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])


class UserCreatedResponse(BaseModel):
    """Response after creating a user."""

    id: str
    username: str
    email: str | None = None
    roles: list[str]


@router.post("/users", response_model=UserCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserCreatedResponse:
    """Create a new user (development helper; production should use a script)."""
    # Check duplicate
    existing = await db.execute(
        select(User).where(User.username == body.username),
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{body.username}' already exists",
        )

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Assign roles
    for role_name in body.roles:
        role_result = await db.execute(
            select(Role).where(Role.name == role_name),
        )
        role = role_result.scalar_one_or_none()
        if role is not None:
            from app.models.user import UserRole
            db.add(UserRole(user_id=user.id, role_id=role.id))

    await db.flush()

    # Reload with roles
    await db.refresh(user)
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.roles)),
    )
    user = result.scalar_one()

    return UserCreatedResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        roles=[r.name for r in user.roles],
    )
