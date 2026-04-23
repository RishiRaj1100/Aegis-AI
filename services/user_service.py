"""
AegisAI - User Service
Handles user registration, authentication, token generation, and password hashing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
import jwt
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserService:
    """
    User authentication and password management service.
    Uses bcrypt for password hashing and PyJWT for token generation.
    """

    def __init__(self, mongo_service) -> None:
        """
        Initialize UserService with a MongoDB connection.

        Args:
            mongo_service: MongoDBService instance for database access.
        """
        self.mongo = mongo_service

    # ══════════════════════════════════════════════════════════════════════════
    # Password Operations
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plaintext password using bcrypt.

        Args:
            password: Plaintext password string.

        Returns:
            Bcrypt hashed password string.
        """
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify a plaintext password against a bcrypt hash.

        Args:
            password: Plaintext password to verify.
            hashed: Bcrypt hashed password from database.

        Returns:
            True if password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as exc:
            logger.error("Password verification failed: %s", exc)
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # JWT Token Operations
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def create_access_token(user_id: str, email: str, expires_in_hours: Optional[int] = None) -> str:
        """
        Generate a JWT access token.

        Args:
            user_id: Unique user identifier.
            email: User email address.
            expires_in_hours: Token expiration in hours (default from settings).

        Returns:
            Encoded JWT token string.
        """
        expires_in = expires_in_hours or settings.JWT_EXPIRATION_HOURS
        expire = datetime.utcnow() + timedelta(hours=expires_in)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return token

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """
        Generate a JWT refresh token with longer expiration.

        Args:
            user_id: Unique user identifier.

        Returns:
            Encoded JWT refresh token string.
        """
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Decoded payload dict if valid, None if invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.debug("Invalid token: %s", exc)
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # User CRUD Operations
    # ══════════════════════════════════════════════════════════════════════════

    async def register_user(self, name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Register a new user.

        Args:
            name: User full name.
            email: User email (must be unique).
            password: Plaintext password.

        Returns:
            User document (without password hash) if successful, None if email already exists.
        """
        users_col = self.mongo.db[settings.USERS_COLLECTION]

        # Check if email already exists
        existing = await users_col.find_one({"email": email})
        if existing:
            logger.warning("Registration attempted with existing email: %s", email)
            return None

        # Create new user document
        user_doc = {
            "name": name,
            "email": email,
            "password_hash": self.hash_password(password),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
        }

        result = await users_col.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        user_doc.pop("password_hash", None)  # Don't return password hash

        logger.info("User registered: %s (%s)", name, email)
        return user_doc

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by email.

        Args:
            email: User email address.

        Returns:
            User document if found, None otherwise.
        """
        users_col = self.mongo.db[settings.USERS_COLLECTION]
        user = await users_col.find_one({"email": email})
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a user by ID.

        Args:
            user_id: User ID (from JWT subject claim).

        Returns:
            User document (without password hash) if found, None otherwise.
        """
        from bson import ObjectId

        users_col = self.mongo.db[settings.USERS_COLLECTION]
        try:
            user = await users_col.find_one({"_id": ObjectId(user_id)})
            if user:
                user.pop("password_hash", None)
                user["_id"] = str(user["_id"])
            return user
        except Exception as exc:
            logger.error("Error retrieving user by ID: %s", exc)
            return None

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user by email and password.

        Args:
            email: User email address.
            password: Plaintext password.

        Returns:
            User document (without password hash) if credentials are valid, None otherwise.
        """
        user = await self.get_user_by_email(email)
        if not user:
            logger.warning("Authentication failed: email not found (%s)", email)
            return None

        if not user.get("is_active", False):
            logger.warning("Authentication failed: user inactive (%s)", email)
            return None

        if not self.verify_password(password, user.get("password_hash", "")):
            logger.warning("Authentication failed: invalid password (%s)", email)
            return None

        user.pop("password_hash", None)
        user["_id"] = str(user["_id"])
        logger.info("User authenticated: %s", email)
        return user


# ──────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ──────────────────────────────────────────────────────────────────────────────

_user_service: Optional[UserService] = None


def get_user_service(mongo_service) -> UserService:
    """Get or create the UserService singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService(mongo_service)
    return _user_service
