"""Reasoning service with Groq primary and OpenRouter Mistral fallback."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from config.settings import get_settings
from services.groq_service import get_groq_service

logger = logging.getLogger(__name__)
settings = get_settings()


class ReasoningService:
    """Provides robust text and JSON reasoning calls with provider fallback."""

    def __init__(self) -> None:
        self.groq = get_groq_service()
        try:
            from services.local_inference_service import get_local_inference_service
            self.local_brain = get_local_inference_service()
        except ImportError:
            self.local_brain = None

    async def _openrouter_chat(
        self,
        *,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        payload: Dict[str, Any] = {
            "model": settings.OPENROUTER_REASONING_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                settings.OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions",
                headers=headers,
                json=payload,
            )
            if not resp.is_success:
                raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:300]}")
            data = resp.json()

        try:
            return str(data["choices"][0]["message"]["content"] or "")
        except Exception as exc:
            raise RuntimeError(f"OpenRouter malformed response: {exc}") from exc

    async def chat_with_fallback(
        self,
        *,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        # 1. Try Local Fine-Tuned Brain (if enabled and available)
        if self.local_brain and self.local_brain.enabled and getattr(self.local_brain, 'status', None) == 'READY':
            try:
                logger.info("Attempting reasoning via local fine-tuned brain...")
                text = await self.local_brain.chat(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return {"text": text, "provider": "local-fine-tuned"}
            except Exception as local_exc:
                logger.warning("Local brain failed; falling back to APIs: %s", local_exc)

        # 2. Try Groq (Primary API)
        try:
            text = await self.groq.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            return {"text": text, "provider": "groq"}
        except Exception as groq_exc:
            logger.warning("Groq reasoning failed; falling back to OpenRouter Mistral: %s", groq_exc)
            text = await self._openrouter_chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
            return {"text": text, "provider": "openrouter-mistral"}


_reasoning_service: ReasoningService | None = None


def get_reasoning_service() -> ReasoningService:
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService()
    return _reasoning_service
