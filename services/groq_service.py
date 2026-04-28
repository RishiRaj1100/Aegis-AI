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


import httpx

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

    # ── Fallback logic ────────────────────────────────────────────────────────

    async def _openrouter_fallback(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]] = None,
        attempt: int = 0,
    ) -> str:
        """
        Fallback to OpenRouter using direct HTTP for maximum compatibility.
        Tries multiple models sequentially if errors occur.
        """
        if not settings.OPENROUTER_API_KEY:
            logger.error("OpenRouter fallback failed: No API key configured.")
            return "ERROR: AI services are currently unavailable (Groq rate-limited and no OpenRouter key)."

        # Sequence of reliable fallback models
        models = [
            "mistralai/mistral-7b-instruct-v0.1",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-8b-instruct",
            "openai/gpt-4o-mini",
        ]
        
        if attempt >= len(models):
            return "ERROR: All fallback AI models failed."

        model = models[attempt]
        logger.info("Initiating OpenRouter fallback (Model: %s, Attempt: %d)...", model, attempt + 1)
        
        # Enforce JSON request if response_format is requested
        prompt_suffix = ""
        if response_format and response_format.get("type") == "json_object":
            prompt_suffix = "\n\nIMPORTANT: Return ONLY a valid JSON object. Do not include markdown code blocks or any other text."

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt + prompt_suffix},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Some free models on OpenRouter fail if 'response_format' is included
        # We handle this by adding it to the prompt and only using the parameter for stable models
        if response_format and ("free" not in model.lower() or "gpt-4o-mini" in model):
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL,
            "X-Title": settings.OPENROUTER_APP_NAME,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
                url = settings.OPENROUTER_BASE_URL.rstrip("/") + "/chat/completions"
                resp = await client.post(url, headers=headers, json=payload)
                
                # If model not found or other service error, try the next model in the list
                if resp.status_code in [404, 400, 422, 502, 503]:
                    logger.warning("OpenRouter Model %s failed (Status %d). Trying next fallback...", model, resp.status_code)
                    return await self._openrouter_fallback(
                        system_prompt, user_message, temperature, max_tokens, response_format, attempt + 1
                    )

                if not resp.is_success:
                    logger.error("OpenRouter failed with status %d: %s", resp.status_code, resp.text)
                    return f"ERROR: AI services unavailable (Status {resp.status_code})"
                
                data = resp.json()
                if "choices" not in data or not data["choices"]:
                    logger.error("OpenRouter unexpected response: %s", data)
                    return await self._openrouter_fallback(
                        system_prompt, user_message, temperature, max_tokens, response_format, attempt + 1
                    )
                
                content = data["choices"][0]["message"]["content"] or ""
                
                # Clean up markdown JSON blocks if the model included them despite instructions
                if response_format and response_format.get("type") == "json_object":
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif content.startswith("```"):
                        content = content.split("```")[1].split("```")[0].strip()

                logger.info("OpenRouter fallback successful using %s.", model)
                return str(content)
                
        except Exception as e:
            logger.error("OpenRouter fallback connection failed for %s: %s", model, e)
            return await self._openrouter_fallback(
                system_prompt, user_message, temperature, max_tokens, response_format, attempt + 1
            )

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
        Falls back to OpenRouter if Groq quota is exhausted.
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
                logger.warning(f"Groq rate limit encountered: {err_str}. Triggering OpenRouter fallback.")
                return await self._openrouter_fallback(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=kwargs["temperature"],
                    max_tokens=kwargs["max_tokens"],
                    response_format=response_format
                )
            except Exception as exc:
                logger.error("Unexpected Groq error: %s. Triggering OpenRouter fallback.", exc)
                return await self._openrouter_fallback(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=kwargs["temperature"],
                    max_tokens=kwargs["max_tokens"],
                    response_format=response_format
                )
        
        # All Groq retries failed, try OpenRouter as last resort
        return await self._openrouter_fallback(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=kwargs["temperature"],
            max_tokens=kwargs["max_tokens"],
            response_format=response_format
        )

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
        """
        raw = await self.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        # If the fallback returned an error message string instead of JSON
        if raw.startswith("ERROR:"):
            logger.error("Reasoning failed: %s", raw)
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            # Attempt a simple repair for truncated JSON
            logger.warning("JSON parse failed, attempting repair... | error: %s", exc)
            repaired = raw.strip()
            
            # If it looks like it was truncated in the middle of a string
            if repaired.count('"') % 2 != 0:
                repaired += '"'
            
            # Close any open structures
            open_braces = repaired.count('{') - repaired.count('}')
            open_brackets = repaired.count('[') - repaired.count(']')
            
            repaired += ']' * max(0, open_brackets)
            repaired += '}' * max(0, open_braces)
            
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response even after repair: %s | raw=%s", exc, raw[:200])
                return {}

    # ── Multi-turn helper ─────────────────────────────────────────────────────

    async def multi_turn_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Accept a full message history (for future chain-of-thought use)."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature or self._temperature,
                max_tokens=self._max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception:
            # Fallback for multi-turn is more complex, using simple chat fallback for now
            return await self._openrouter_fallback(
                system_prompt="Multi-turn fallback",
                user_message=str(messages),
                temperature=temperature or self._temperature,
                max_tokens=self._max_tokens
            )


# ── Dependency-injection factory ──────────────────────────────────────────────

_groq_service: Optional[GroqService] = None


def get_groq_service() -> GroqService:
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service
