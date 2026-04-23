"""
AegisAI - Groq LLM Service
Wraps the Groq Python SDK for chat-completion calls used by every reasoning agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from groq import AsyncGroq, RateLimitError

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GroqService:
    """
    Thin async wrapper around the Groq SDK.
    All agents share a single instance injected via FastAPI dependency injection.
    """

    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self._model = settings.GROQ_MODEL
        self._temperature = settings.GROQ_TEMPERATURE
        self._max_tokens = settings.GROQ_MAX_TOKENS

    # ── Core completion helper ────────────────────────────────────────────────

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Send a single-turn chat request to Groq and return the assistant text.
        Retries up to 3 times on rate-limit (429) with exponential back-off.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self._temperature,
            "max_tokens": max_tokens or self._max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        logger.debug("Groq request | model=%s | tokens=%s", self._model, kwargs["max_tokens"])

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                logger.debug("Groq response length: %d chars", len(content))
                return content
            except RateLimitError as exc:
                last_err = exc
                err_str = str(exc)
                # Daily token quota (TPD) does NOT recover in minutes — fail fast.
                if "tokens per day" in err_str or "TPD" in err_str:
                    logger.error(
                        "Groq daily token quota exhausted — failing immediately (no retry). "
                        "Quota resets in ~24 h. Used too many tokens today."
                    )
                    raise  # re-raise immediately; no point waiting
                # Per-minute / per-request rate limit — wait and retry.
                match = re.search(r"(\d+)m([\d.]+)s", err_str)
                wait = (int(match.group(1)) * 60 + float(match.group(2))) if match else 10.0 * (2 ** attempt)
                wait = min(wait + 2, 65)  # cap at ~1 min
                logger.warning(
                    "Groq rate limit (attempt %d/3) — waiting %.0fs before retry",
                    attempt + 1, wait,
                )
                await asyncio.sleep(wait)
        raise last_err  # all retries exhausted

    # ── JSON helper ───────────────────────────────────────────────────────────

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Like `chat()` but enforces JSON response format and parses the result.
        Falls back to empty dict on parse error.
        Pass max_tokens to override the global default for large JSON responses.
        """
        raw = await self.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Groq JSON response: %s | raw=%s", exc, raw[:200])
            return {}

    # ── Multi-turn helper ─────────────────────────────────────────────────────

    async def multi_turn_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Accept a full message history (for future chain-of-thought use)."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature or self._temperature,
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content or ""


# ── Dependency-injection factory ──────────────────────────────────────────────

_groq_service: Optional[GroqService] = None


def get_groq_service() -> GroqService:
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service
