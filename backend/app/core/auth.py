"""
CPIS V1 — Authentication and authorization utilities.

- Password hashing with bcrypt (via passlib)
- JWT token creation/verification (via PyJWT)
- get_current_user FastAPI dependency
- require_roles dependency factory
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import get_settings
from app.core.database import get_db
from app.models.user import User

settings = get_settings()

# ── Password hashing ───────────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _pwd_ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return _pwd_ctx.verify(password, hashed)


# ── JWT ────────────────────────────────────────────────────────────

_ALGORITHM = "HS256"
_DEFAULT_EXPIRY = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def _get_secret_key() -> str:
    """Return the SECRET_KEY, raising if empty in production."""
    key = settings.SECRET_KEY
    if settings.ENVIRONMENT == "production" and not key:
        raise RuntimeError(
            "SECRET_KEY is not set — it is required in production.",
        )
    if not key:
        # Development fallback (never use in production)
        key = "dev-secret-key-change-in-production"
    return key


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to embed (must include at least ``sub``).
        expires_delta: Token lifetime (defaults to 24 hours).

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or _DEFAULT_EXPIRY)
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, _get_secret_key(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises:
        HTTPException(401) if the token is expired, malformed, or invalid.
    """
    try:
        payload = jwt.decode(
            token, _get_secret_key(), algorithms=[_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── FastAPI dependencies ──────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """FastAPI dependency — extract and validate the current user from a JWT.

    Requires a ``Bearer`` token in the ``Authorization`` header.
    Returns the ``User`` ORM instance (with roles loaded).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    sub: str | None = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Resolve user — sub can be a UUID string or username
    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(sub) if _is_uuid(sub) else User.username == sub)
        .options(selectinload(User.roles)),
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is deactivated",
        )

    return user


def require_roles(*roles: str) -> Callable:
    """Return a FastAPI dependency that checks the current user has **all** given roles.

    Usage::

        @router.post("/tasks")
        async def create_task(
            user: Annotated[User, Depends(require_roles("admin", "operator"))],
        ):
            ...
    """
    required = set(roles)

    async def _role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        user_role_names = {r.name for r in current_user.roles}

        # Admin always passes
        if "admin" in user_role_names:
            return current_user

        if not required.issubset(user_role_names):
            missing = required - user_role_names
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role(s): {', '.join(sorted(missing))}",
            )
        return current_user

    return _role_checker


# ── Internal helpers ──────────────────────────────────────────────


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
