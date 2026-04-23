"""
Security & RBAC API Router
Role management, API keys, 2FA, audit logs
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio

from services.rbac_service import (
    RBACService,
    Role,
    Permission,
    get_rbac_service,
)

router = APIRouter(prefix="/api/security", tags=["security"])


def _require_user_id(user_id: str) -> str:
    user_id = (user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")
    return user_id


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    from core.pipeline import get_database

    result = get_database()
    if asyncio.iscoroutinefunction(get_database):
        return await result
    return result


# ── Role Management ──────────────────────────────────────────────────────────

@router.post("/roles/assign")
async def assign_role(
    user_id: str,
    role: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Assign role to user (admin only)."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        role_enum = Role(role)
        success = await service.set_user_role(user_id, role_enum)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to assign role")

        return {
            "status": "success",
            "user_id": user_id,
            "role": role,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles/{user_id}")
async def get_user_role(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get user's current role."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        role = await service.get_user_role(user_id)

        return {
            "status": "success",
            "user_id": user_id,
            "role": role.value,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Permission Checking ──────────────────────────────────────────────────────

@router.get("/permissions/{user_id}")
async def check_permission(
    user_id: str,
    permission: str = Query(..., description="Permission to check"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Check if user has specific permission."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        perm_enum = Permission(permission)
        has_perm = await service.has_permission(user_id, perm_enum)

        return {
            "status": "success",
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_perm,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {permission}")
    except HTTPException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API Key Management ───────────────────────────────────────────────────────

@router.post("/api-keys/create")
async def create_api_key(
    user_id: str,
    name: str = Query(...),
    expires_in_days: int = Query(90, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create new API key."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        key = await service.create_api_key(
            user_id=user_id,
            name=name,
            expires_in_days=expires_in_days,
        )

        if not key:
            raise HTTPException(status_code=500, detail="Failed to create API key")

        return {
            "status": "success",
            "api_key": key,
            "message": "Save this key securely - it won't be shown again",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys/revoke")
async def revoke_api_key(
    user_id: str,
    key_name: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Revoke an API key."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        success = await service.revoke_api_key(user_id, key_name)

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {
            "status": "success",
            "message": "API key revoked",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-keys")
async def get_user_api_keys(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get all API keys for user."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        keys = await service.get_user_api_keys(user_id)

        return {
            "status": "success",
            "count": len(keys),
            "api_keys": keys,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Two-Factor Authentication ────────────────────────────────────────────────

@router.post("/mfa/enable")
async def enable_mfa(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Enable 2FA for user."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        secret = await service.enable_mfa(user_id)

        if not secret:
            raise HTTPException(status_code=500, detail="Failed to enable MFA")

        return {
            "status": "success",
            "secret": secret,
            "message": "Scan QR code with authenticator app",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/confirm")
async def confirm_mfa(
    user_id: str,
    code: str = Query(..., description="6-digit TOTP code"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Confirm 2FA setup."""
    try:
        user_id = _require_user_id(user_id)
        service = get_rbac_service(db)

        success = await service.confirm_mfa(user_id, code)

        if not success:
            raise HTTPException(status_code=400, detail="Invalid code")

        return {
            "status": "success",
            "message": "2FA enabled successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Audit Logging ────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    user_id: str = Query(None),
    action: str = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get audit logs with filtering."""
    try:
        user_id = _require_user_id(user_id) if user_id is not None else None
        service = get_rbac_service(db)

        logs = await service.get_audit_logs(
            user_id=user_id,
            action=action,
            days=days,
            limit=limit,
        )

        return {
            "status": "success",
            "count": len(logs),
            "audit_logs": logs,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security-report")
async def get_security_report(
    user_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get security report."""
    try:
        user_id = _require_user_id(user_id) if user_id is not None else None
        service = get_rbac_service(db)

        report = await service.get_security_report(user_id)

        return {
            "status": "success",
            "report": report,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
