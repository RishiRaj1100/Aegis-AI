"""
AegisAI - Utility Helpers
Common utilities used across agents, services, and routers.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── Text utilities ─────────────────────────────────────────────────────────────

def truncate(text: str, max_chars: int = 200, ellipsis: str = "…") -> str:
    """Return truncated text with trailing ellipsis if over limit."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(ellipsis)] + ellipsis


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def sanitise_goal(goal: str) -> str:
    """Strip leading/trailing whitespace and normalise internal spaces."""
    return " ".join(goal.split())


# ── Language helpers ───────────────────────────────────────────────────────────

_LANGUAGE_NAMES: Dict[str, str] = {
    "en-IN": "English",
    "en-US": "English",
    "hi-IN": "Hindi (हिंदी)",
    "ta-IN": "Tamil (தமிழ்)",
    "te-IN": "Telugu (తెలుగు)",
    "bn-IN": "Bengali (বাংলা)",
    "mr-IN": "Marathi (मराठी)",
    "gu-IN": "Gujarati (ગુજરાતી)",
    "kn-IN": "Kannada (ಕನ್ನಡ)",
    "ml-IN": "Malayalam (മലയാളം)",
    "pa-IN": "Punjabi (ਪੰਜਾਬੀ)",
    "od-IN": "Odia (ଓଡ଼ିଆ)",
}


def get_language_name(language_code: str) -> str:
    """Return the human-readable language name for a BCP-47 code."""
    return _LANGUAGE_NAMES.get(language_code, "English")


def language_instruction(language_code: str) -> str:
    """Return a strong instruction for LLM to respond in the given language."""
    lang = get_language_name(language_code)
    if language_code in ("en-IN", "en-US"):
        return ""
    return (
        f"\n\nIMPORTANT — LANGUAGE REQUIREMENT: Write ALL text content in your response "
        f"in {lang}. This includes titles, descriptions, insights, execution plan, "
        f"reasoning, risks, opportunities — every string value in the JSON must be "
        f"written in {lang}. Do NOT use English for any content field."
    )


# ── Audio / Base64 helpers ─────────────────────────────────────────────────────

def bytes_to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def base64_to_bytes(b64_string: str) -> bytes:
    return base64.b64decode(b64_string)


def audio_file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return bytes_to_base64(f.read())


def detect_audio_format(audio_bytes: bytes) -> str:
    """Detect audio format from magic bytes."""
    if audio_bytes[:4] == b"RIFF":
        return "wav"
    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
        return "mp3"
    return "wav"  # default


# ── Hashing ───────────────────────────────────────────────────────────────────

def hash_goal(goal: str) -> str:
    """Create a short deterministic hash for a goal string (cache keying)."""
    return hashlib.sha256(goal.encode()).hexdigest()[:16]


# ── Date / time ───────────────────────────────────────────────────────────────

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Dict helpers ──────────────────────────────────────────────────────────────

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge `override` into `base`. `override` wins on conflicts."""
    result = {**base}
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def remove_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of `d` without keys whose values are None."""
    return {k: v for k, v in d.items() if v is not None}


# ── Confidence formatting ─────────────────────────────────────────────────────

def format_confidence(confidence: float) -> str:
    """Return a human-readable confidence string, e.g. '73.5%'."""
    return f"{confidence:.1f}%"


def confidence_emoji(confidence: float) -> str:
    """Return a visual indicator for the confidence level."""
    if confidence >= 70:
        return "✅"
    if confidence >= 40:
        return "⚠️"
    return "❌"
