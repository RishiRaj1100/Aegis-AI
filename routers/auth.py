"""
AegisAI - Auth Router
POST /auth/register  – Register a new user
POST /auth/login     – Authenticate and get tokens
POST /auth/refresh   – Refresh access token using refresh token
GET  /auth/me        – Get current authenticated user info
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from services.user_service import UserService
from utils.helpers import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """POST /auth/register request body."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: str = Field(..., description="Email address (must be unique)")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 chars)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "password": "SecurePass123!",
            }
        }
    )


class LoginRequest(BaseModel):
    """POST /auth/login request body."""
    email: str
    password: str


class RefreshRequest(BaseModel):
    """POST /auth/refresh request body."""
    refresh_token: str = Field(..., description="Refresh token from login response")


class UserResponse(BaseModel):
    """User data in responses (no password)."""
    id: str = Field(alias="_id")
    name: str
    email: str
    created_at: datetime | str

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | str) -> str:
        """Convert datetime to ISO format string."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class AuthResponse(BaseModel):
    """Successful auth response with tokens."""
    user: UserResponse
    access_token: str = Field(..., description="JWT access token (short-lived)")
    refresh_token: str = Field(..., description="JWT refresh token (long-lived)")
    token_type: str = "bearer"


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str


# ══════════════════════════════════════════════════════════════════════════════
# Dependencies
# ══════════════════════════════════════════════════════════════════════════════

def _get_mongo():
    """Get MongoDB service — resolved at runtime via app state."""
    from main import get_pipeline
    pipeline = get_pipeline()
    return pipeline.memory.mongo


def _get_user_service(mongo=Depends(_get_mongo)) -> UserService:
    """Get UserService using MongoDB."""
    from services.user_service import get_user_service
    return get_user_service(mongo)


async def get_current_user(
    authorization: str = Header(None),
    user_service: UserService = Depends(_get_user_service),
) -> Dict[str, Any]:
    """
    Extract and verify JWT token from Authorization header.
    Returns a guest user if no token is provided (allows unauthenticated access for demo).
    """
    # ── Guest / no-auth mode: return a virtual guest user ─────────────────────
    if not authorization:
        return {
            "sub": "guest",
            "email": "guest@aegisai.local",
            "name": "Guest",
            "type": "access",
        }

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        # Malformed header — still fall back to guest rather than hard-fail
        return {
            "sub": "guest",
            "email": "guest@aegisai.local",
            "name": "Guest",
            "type": "access",
        }

    token = parts[1]
    payload = user_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid",
        )

    return payload


def require_current_user_id(payload: Dict[str, Any]) -> str:
    """Return a non-empty authenticated user id from token payload."""
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user id.",
        )
    return user_id.strip()


# ══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Email already registered or validation error"},
    },
    summary="Register a new user",
    description="Create a new user account with email and password. Returns access and refresh tokens.",
)
async def register(
    request: RegisterRequest,
    user_service: UserService = Depends(_get_user_service),
) -> AuthResponse:
    """Register a new user and return authentication tokens."""
    # Register the user
    user = await user_service.register_user(
        name=request.name,
        email=request.email,
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    # Generate tokens
    access_token = user_service.create_access_token(
        user_id=user["_id"],
        email=user["email"],
    )
    refresh_token = user_service.create_refresh_token(user_id=user["_id"])

    return AuthResponse(
        user=UserResponse(**user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
    },
    summary="Authenticate user",
    description="Log in with email and password. Returns access and refresh tokens.",
)
async def login(
    request: LoginRequest,
    user_service: UserService = Depends(_get_user_service),
) -> AuthResponse:
    """Authenticate user and return tokens."""
    user = await user_service.authenticate_user(
        email=request.email,
        password=request.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Generate tokens
    access_token = user_service.create_access_token(
        user_id=user["_id"],
        email=user["email"],
    )
    refresh_token = user_service.create_refresh_token(user_id=user["_id"])

    return AuthResponse(
        user=UserResponse(**user),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
    summary="Refresh access token",
    description="Use a refresh token to get a new access token without re-entering credentials.",
)
async def refresh_token(
    request: RefreshRequest,
    user_service: UserService = Depends(_get_user_service),
) -> Dict[str, str]:
    """Refresh access token using a refresh token."""
    payload = user_service.verify_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id = payload.get("sub")
    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Generate new access token
    new_access_token = user_service.create_access_token(
        user_id=user["_id"],
        email=user["email"],
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    },
    summary="Get current user info",
    description="Retrieve the authenticated user's profile information.",
)
async def get_me(
    payload: Dict[str, Any] = Depends(get_current_user),
    user_service: UserService = Depends(_get_user_service),
) -> UserResponse:
    """Get current authenticated user."""
    user_id = payload.get("sub")

    user = await user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return UserResponse(**user)
