"""
SECURITY HARDENING SERVICE — Key Rotation, Rate Limiting, Centralized Logging

Purpose: Implement production-grade security with automated key rotation,
rate limiting, and centralized audit logging
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
import os
import hashlib
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets to rotate."""
    PINECONE_API_KEY = "pinecone_api_key"
    GROQ_API_KEY = "groq_api_key"
    MONGODB_URI = "mongodb_uri"
    REDIS_URL = "redis_url"


@dataclass
class SecretRotationLog:
    """Record of a secret rotation."""
    secret_type: SecretType
    rotation_date: datetime
    previous_key_hash: str  # Hash of old key (don't store plaintext)
    new_key_hash: str  # Hash of new key
    success: bool
    error_message: Optional[str] = None


@dataclass
class RateLimitViolation:
    """Record of a rate limit violation."""
    timestamp: datetime
    client_id: str
    endpoint: str
    requests_count: int
    limit: int
    action_taken: str  # "warn", "throttle", "block"


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.client_requests = defaultdict(list)  # client_id -> [timestamps]
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for client.
        
        Args:
            client_id: Unique identifier (IP, API key, user_id)
        
        Returns:
            True if request should be allowed, False if rate limited
        """
        try:
            now = time.time()
            window_start = now - 60  # 1 minute window
            
            # Clean old requests
            self.client_requests[client_id] = [
                ts for ts in self.client_requests[client_id]
                if ts > window_start
            ]
            
            # Check if within limit
            if len(self.client_requests[client_id]) < self.requests_per_minute:
                self.client_requests[client_id].append(now)
                return True
            else:
                return False
        
        except Exception as e:
            logger.error(f"[Security] Error checking rate limit: {e}")
            return True  # Allow on error (fail open)
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        window_start = now - 60
        
        valid_requests = [
            ts for ts in self.client_requests[client_id]
            if ts > window_start
        ]
        
        return max(0, self.requests_per_minute - len(valid_requests))


class SecretManager:
    """Manages secret rotation and validation."""
    
    def __init__(self):
        from services.mongodb_service import get_db
        
        self.db = get_db()
        self._setup_collections()
        
        # Default rotation intervals (days)
        self.rotation_intervals = {
            SecretType.PINECONE_API_KEY: 7,  # Weekly
            SecretType.GROQ_API_KEY: 30,  # Monthly
            SecretType.MONGODB_URI: 30,  # Monthly
            SecretType.REDIS_URL: 30,  # Monthly
        }
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        rotations = self.db["secret_rotations"]
        rotations.create_index([("secret_type", 1)])
        rotations.create_index([("rotation_date", -1)])
        rotations.create_index([("success", 1)])
    
    def _hash_secret(self, secret: str) -> str:
        """Hash secret for storage (never store plaintext)."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def check_rotation_needed(self, secret_type: SecretType) -> Tuple[bool, int]:
        """
        Check if a secret needs rotation.
        
        Args:
            secret_type: Type of secret to check
        
        Returns:
            Tuple of (needs_rotation, days_since_rotation)
        """
        try:
            # Get last rotation
            last_rotation = self.db["secret_rotations"].find_one(
                {"secret_type": secret_type.value, "success": True},
                sort=[("rotation_date", -1)]
            )
            
            interval = self.rotation_intervals.get(secret_type, 30)
            
            if not last_rotation:
                # Never rotated, needs rotation
                return True, 999
            
            days_since = (datetime.utcnow() - last_rotation["rotation_date"]).days
            needs_rotation = days_since >= interval
            
            return needs_rotation, days_since
        
        except Exception as e:
            logger.error(f"[Security] Error checking rotation: {e}")
            return False, 0
    
    def log_rotation(self, secret_type: SecretType, old_key: str,
                    new_key: str, success: bool,
                    error_message: Optional[str] = None) -> Dict:
        """
        Log a secret rotation event.
        
        Args:
            secret_type: Type of secret
            old_key: Old secret (will be hashed)
            new_key: New secret (will be hashed)
            success: Whether rotation succeeded
            error_message: Error details if failed
        
        Returns:
            Dict with log status
        """
        try:
            old_hash = self._hash_secret(old_key) if old_key else None
            new_hash = self._hash_secret(new_key)
            
            log_entry = {
                "secret_type": secret_type.value,
                "rotation_date": datetime.utcnow(),
                "previous_key_hash": old_hash,
                "new_key_hash": new_hash,
                "success": success,
                "error_message": error_message,
            }
            
            self.db["secret_rotations"].insert_one(log_entry)
            
            status = "success" if success else "failed"
            logger.warning(f"[Security] Secret rotation {status}: {secret_type.value}")
            
            return {"logged": True, "success": success}
        
        except Exception as e:
            logger.error(f"[Security] Error logging rotation: {e}")
            return {"logged": False, "error": str(e)}
    
    def get_rotation_status(self) -> Dict:
        """Get rotation status for all secrets."""
        try:
            status = {}
            
            for secret_type in SecretType:
                needs_rotation, days_since = self.check_rotation_needed(secret_type)
                interval = self.rotation_intervals.get(secret_type, 30)
                
                status[secret_type.value] = {
                    "needs_rotation": needs_rotation,
                    "days_since_rotation": days_since,
                    "rotation_interval_days": interval,
                    "days_until_rotation": max(0, interval - days_since),
                }
            
            return status
        
        except Exception as e:
            logger.error(f"[Security] Error getting rotation status: {e}")
            return {}


class CORSManager:
    """Manages CORS (Cross-Origin Resource Sharing) configuration."""
    
    @staticmethod
    def get_allowed_origins() -> list:
        """Get list of allowed CORS origins."""
        try:
            # Get from environment or use defaults
            allowed = os.environ.get("ALLOWED_ORIGINS", "").split(",")
            
            # Add defaults
            allowed.extend([
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ])
            
            # Filter empty strings
            allowed = [origin.strip() for origin in allowed if origin.strip()]
            
            return list(set(allowed))  # Remove duplicates
        
        except Exception as e:
            logger.warning(f"[Security] Error getting CORS origins: {e}")
            return ["http://localhost:3000", "http://localhost:8000"]
    
    @staticmethod
    def get_cors_middleware_config() -> Dict:
        """Get CORS middleware configuration for FastAPI."""
        return {
            "allow_origins": CORSManager.get_allowed_origins(),
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["*"],
            "max_age": 3600,  # 1 hour cache
        }


class CentralizedLogger:
    """Centralized logging for audit trail."""
    
    def __init__(self):
        from services.mongodb_service import get_db
        
        self.db = get_db()
        self._setup_collections()
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        audit_log = self.db["audit_log"]
        audit_log.create_index([("timestamp", -1)])
        audit_log.create_index([("user_id", 1), ("timestamp", -1)])
        audit_log.create_index([("event_type", 1)])
        audit_log.create_index([("severity", 1)])
    
    def log_event(self, event_type: str, severity: str, user_id: Optional[str],
                 action: str, details: Optional[Dict] = None,
                 status: str = "success") -> Dict:
        """
        Log an event to audit trail.
        
        Args:
            event_type: Type of event (api_call, auth, security, system)
            severity: Severity level (info, warning, error, critical)
            user_id: User identifier (if applicable)
            action: Action description
            details: Optional additional details
            status: Status of action
        
        Returns:
            Dict with logging status
        """
        try:
            event = {
                "timestamp": datetime.utcnow(),
                "event_type": event_type,
                "severity": severity,
                "user_id": user_id,
                "action": action,
                "status": status,
                "details": details or {},
            }
            
            self.db["audit_log"].insert_one(event)
            
            # Also log to Python logger
            log_level = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }.get(severity, logging.INFO)
            
            logger.log(log_level, f"[Audit] {event_type}: {action}")
            
            return {"logged": True}
        
        except Exception as e:
            logger.error(f"[Security] Error logging event: {e}")
            return {"logged": False, "error": str(e)}
    
    def get_audit_log(self, user_id: Optional[str] = None,
                     event_type: Optional[str] = None,
                     limit: int = 50) -> list:
        """
        Retrieve audit log entries.
        
        Args:
            user_id: Filter by user (optional)
            event_type: Filter by event type (optional)
            limit: Max results
        
        Returns:
            List of audit log entries
        """
        try:
            query = {}
            
            if user_id:
                query["user_id"] = user_id
            if event_type:
                query["event_type"] = event_type
            
            entries = list(self.db["audit_log"].find(query)
                          .sort("timestamp", -1)
                          .limit(limit))
            
            return [
                {
                    "timestamp": e.get("timestamp").isoformat() if e.get("timestamp") else None,
                    "event_type": e.get("event_type"),
                    "severity": e.get("severity"),
                    "user_id": e.get("user_id"),
                    "action": e.get("action"),
                    "status": e.get("status"),
                }
                for e in entries
            ]
        
        except Exception as e:
            logger.error(f"[Security] Error retrieving audit log: {e}")
            return []
    
    def get_security_summary(self) -> Dict:
        """Get security summary (suspicious activities, etc.)."""
        try:
            # Count events by severity
            pipeline = [
                {"$group": {
                    "_id": "$severity",
                    "count": {"$sum": 1}
                }},
            ]
            
            severity_counts = list(self.db["audit_log"].aggregate(pipeline))
            
            # Recent critical events
            critical_events = list(self.db["audit_log"].find(
                {"severity": "critical"}
            ).sort("timestamp", -1).limit(10))
            
            return {
                "severity_distribution": {
                    item["_id"]: item["count"]
                    for item in severity_counts
                },
                "recent_critical_events": [
                    {
                        "timestamp": e.get("timestamp").isoformat() if e.get("timestamp") else None,
                        "event_type": e.get("event_type"),
                        "action": e.get("action"),
                        "user_id": e.get("user_id"),
                    }
                    for e in critical_events
                ],
            }
        
        except Exception as e:
            logger.error(f"[Security] Error getting security summary: {e}")
            return {}


class SecurityService:
    """Unified security service."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.secret_manager = SecretManager()
        self.centralized_logger = CentralizedLogger()
        
        self._initialized = True
        logger.info("[Security] Service initialized")
    
    def check_rate_limit(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        allowed = self.rate_limiter.is_allowed(client_id)
        remaining = self.rate_limiter.get_remaining(client_id)
        
        if not allowed:
            self.centralized_logger.log_event(
                event_type="security",
                severity="warning",
                user_id=client_id,
                action="rate_limit_exceeded",
                status="blocked"
            )
        
        return allowed, remaining
    
    def get_security_status(self) -> Dict:
        """Get overall security status."""
        try:
            return {
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 60,
                },
                "secret_rotation": self.secret_manager.get_rotation_status(),
                "cors": {
                    "enabled": True,
                    "allowed_origins_count": len(CORSManager.get_allowed_origins()),
                },
                "audit_logging": {
                    "enabled": True,
                    "centralized": True,
                },
                "security_summary": self.centralized_logger.get_security_summary(),
            }
        
        except Exception as e:
            logger.error(f"[Security] Error getting security status: {e}")
            return {"error": str(e)}


# Singleton accessor
def get_security_service() -> SecurityService:
    """Get or create the SecurityService singleton."""
    return SecurityService()
