"""
AegisAI - Advanced Security & RBAC Service
Role-based access control, audit logging, API key management, 2FA
"""

from __future__ import annotations

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass

from motor.motor_asyncio import AsyncIOMotorDatabase
import bcrypt

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"
    GUEST = "guest"


class Permission(str, Enum):
    """System permissions."""
    # Task permissions
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"

    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # User management
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # System administration
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"

    # Security
    SECURITY_AUDIT = "security:audit"
    SECURITY_CONFIG = "security:config"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.ANALYST: {
        Permission.TASK_READ,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.USER_READ,
        Permission.SECURITY_AUDIT,
    },
    Role.USER: {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.ANALYTICS_READ,
    },
    Role.GUEST: {
        Permission.TASK_READ,
        Permission.ANALYTICS_READ,
    },
}


@dataclass
class AuditLog:
    """Audit log entry."""
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]
    status: str  # 'success', 'failure'


class RBACService:
    """
    Role-Based Access Control with audit logging.

    Features:
    - Role and permission management
    - API key generation and validation
    - Audit logging
    - Two-factor authentication
    - Session security
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB."""
        self.db = db
        self.users_collection = db["users"]
        self.roles_collection = db["roles"]
        self.api_keys_collection = db["api_keys"]
        self.audit_logs_collection = db["audit_logs"]
        self.mfa_collection = db["mfa_settings"]

    # ── Role Management ───────────────────────────────────────────────────────

    async def set_user_role(self, user_id: str, role: Role) -> bool:
        """Assign role to user."""
        try:
            await self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"role": role.value, "updated_at": datetime.now()}}
            )

            await self._log_audit(
                user_id=user_id,
                action="role_assignment",
                resource=f"user:{user_id}",
                details={"role": role.value},
            )

            logger.info(f"Role {role.value} assigned to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting user role: {e}")
            return False

    async def get_user_role(self, user_id: str) -> Role:
        """Get user's role."""
        try:
            user = await self.users_collection.find_one({"user_id": user_id})
            if user and "role" in user:
                return Role(user["role"])
            return Role.USER  # Default role
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return Role.USER

    async def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission."""
        try:
            role = await self.get_user_role(user_id)
            return permission in ROLE_PERMISSIONS.get(role, set())

        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False

    async def has_any_permission(
        self,
        user_id: str,
        permissions: List[Permission],
    ) -> bool:
        """Check if user has any of the permissions."""
        for permission in permissions:
            if await self.has_permission(user_id, permission):
                return True
        return False

    async def has_all_permissions(
        self,
        user_id: str,
        permissions: List[Permission],
    ) -> bool:
        """Check if user has all permissions."""
        for permission in permissions:
            if not await self.has_permission(user_id, permission):
                return False
        return True

    # ── API Key Management ────────────────────────────────────────────────────

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[List[Permission]] = None,
        expires_in_days: int = 90,
    ) -> Optional[str]:
        """
        Generate new API key.

        Returns the key (only shown once).
        """
        try:
            # Generate secure random key
            raw_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

            api_key_doc = {
                "user_id": user_id,
                "name": name,
                "key_hash": key_hash,
                "permissions": [p.value for p in (permissions or [])],
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=expires_in_days),
                "last_used": None,
                "is_active": True,
            }

            await self.api_keys_collection.insert_one(api_key_doc)

            await self._log_audit(
                user_id=user_id,
                action="api_key_created",
                resource=f"api_key:{name}",
                details={"expires_in_days": expires_in_days},
            )

            logger.info(f"API key created for user {user_id}")
            return raw_key  # Return unhashed key only once

        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return None

    async def validate_api_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and get associated user."""
        try:
            key_hash = hashlib.sha256(key.encode()).hexdigest()

            api_key = await self.api_keys_collection.find_one({
                "key_hash": key_hash,
                "is_active": True,
                "expires_at": {"$gt": datetime.now()},
            })

            if api_key:
                # Update last_used
                await self.api_keys_collection.update_one(
                    {"_id": api_key["_id"]},
                    {"$set": {"last_used": datetime.now()}}
                )

                return {
                    "user_id": api_key["user_id"],
                    "permissions": [Permission(p) for p in api_key.get("permissions", [])],
                    "expires_at": api_key["expires_at"],
                }

            return None

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None

    async def revoke_api_key(self, user_id: str, key_name: str) -> bool:
        """Revoke an API key."""
        try:
            result = await self.api_keys_collection.update_one(
                {"user_id": user_id, "name": key_name},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                await self._log_audit(
                    user_id=user_id,
                    action="api_key_revoked",
                    resource=f"api_key:{key_name}",
                    details={},
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error revoking API key: {e}")
            return False

    async def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for user (without showing actual keys)."""
        try:
            keys = await self.api_keys_collection.find({
                "user_id": user_id
            }).to_list(None)

            return [
                {
                    "name": key["name"],
                    "created_at": key["created_at"],
                    "expires_at": key["expires_at"],
                    "last_used": key.get("last_used"),
                    "is_active": key["is_active"],
                }
                for key in keys
            ]

        except Exception as e:
            logger.error(f"Error getting user API keys: {e}")
            return []

    # ── Two-Factor Authentication ─────────────────────────────────────────────

    async def enable_mfa(self, user_id: str) -> Optional[str]:
        """
        Enable 2FA for user.

        Returns temporary secret for QR code generation.
        """
        try:
            import pyotp

            # Generate secret
            secret = pyotp.random_base32()

            await self.mfa_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "secret": secret,
                        "enabled": False,  # Not confirmed yet
                        "created_at": datetime.now(),
                    }
                },
                upsert=True
            )

            await self._log_audit(
                user_id=user_id,
                action="mfa_enabled",
                resource=f"user:{user_id}",
                details={},
            )

            return secret

        except Exception as e:
            logger.error(f"Error enabling MFA: {e}")
            return None

    async def confirm_mfa(self, user_id: str, code: str) -> bool:
        """Confirm 2FA setup with verification code."""
        try:
            import pyotp

            mfa = await self.mfa_collection.find_one({"user_id": user_id})

            if not mfa:
                return False

            secret = mfa["secret"]
            totp = pyotp.TOTP(secret)

            if totp.verify(code):
                await self.mfa_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"enabled": True, "confirmed_at": datetime.now()}}
                )

                await self._log_audit(
                    user_id=user_id,
                    action="mfa_confirmed",
                    resource=f"user:{user_id}",
                    details={},
                )

                return True

            return False

        except Exception as e:
            logger.error(f"Error confirming MFA: {e}")
            return False

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify 2FA code during login."""
        try:
            import pyotp

            mfa = await self.mfa_collection.find_one(
                {"user_id": user_id, "enabled": True}
            )

            if not mfa:
                return True  # MFA not enabled

            secret = mfa["secret"]
            totp = pyotp.TOTP(secret)

            return totp.verify(code)

        except Exception as e:
            logger.error(f"Error verifying MFA: {e}")
            return False

    # ── Audit Logging ─────────────────────────────────────────────────────────

    async def _log_audit(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        status: str = "success",
    ) -> None:
        """Log action for audit trail."""
        try:
            audit_entry = {
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "details": details,
                "timestamp": datetime.now(),
                "ip_address": ip_address,
                "status": status,
            }

            await self.audit_logs_collection.insert_one(audit_entry)

        except Exception as e:
            logger.error(f"Error logging audit: {e}")

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filtering."""
        try:
            query: Dict[str, Any] = {
                "timestamp": {
                    "$gte": datetime.now() - timedelta(days=days)
                }
            }

            if user_id:
                query["user_id"] = user_id

            if action:
                query["action"] = action

            logs = await self.audit_logs_collection.find(query).sort(
                "timestamp", -1
            ).to_list(limit)

            return logs

        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []

    # ── Session Security ──────────────────────────────────────────────────────

    async def validate_session(
        self,
        user_id: str,
        session_id: str,
    ) -> bool:
        """Validate user session."""
        try:
            session = await self.db["sessions"].find_one({
                "user_id": user_id,
                "session_id": session_id,
                "expires_at": {"$gt": datetime.now()},
                "is_active": True,
            })

            return session is not None

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False

    async def revoke_session(self, user_id: str, session_id: str) -> bool:
        """Revoke user session."""
        try:
            await self.db["sessions"].update_one(
                {"user_id": user_id, "session_id": session_id},
                {"$set": {"is_active": False, "revoked_at": datetime.now()}}
            )

            return True

        except Exception as e:
            logger.error(f"Error revoking session: {e}")
            return False

    # ── Security Reports ─────────────────────────────────────────────────────

    async def get_security_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get security audit report."""
        try:
            if user_id:
                logs = await self.get_audit_logs(user_id=user_id, days=7)
            else:
                logs = await self.get_audit_logs(days=7)

            failed_actions = [log for log in logs if log.get("status") == "failure"]

            return {
                "total_actions": len(logs),
                "failed_actions": len(failed_actions),
                "audit_logs": logs[:20],  # Last 20
                "risk_level": "high" if len(failed_actions) > 5 else "medium" if len(failed_actions) > 2 else "low",
            }

        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {}


def get_rbac_service(db: AsyncIOMotorDatabase) -> RBACService:
    """Get RBAC service instance."""
    return RBACService(db)
