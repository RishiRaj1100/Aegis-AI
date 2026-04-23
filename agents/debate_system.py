"""
Multi-agent debate engine for AegisAI.

Implements four independent perspectives:
- Optimist
- Risk Analyst
- Executor
- Critic

Primary inference uses Groq. If Groq fails, OpenRouter is used as fallback.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional

import httpx

from config.settings import get_settings
from services.groq_service import GroqService

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass(frozen=True)
class DebateAgentConfig:
    role: str
    temperature: float
    system_prompt: str


class DebateSystem:
    """Runs multi-agent debate and synthesizes a final decision."""

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq
        self.agent_configs: Dict[str, DebateAgentConfig] = {
            "optimist": DebateAgentConfig(
                role="Optimist Agent",
                temperature=0.65,
                system_prompt=(
                    "You are the Optimist Agent in a structured debate. "
                    "Focus only on feasibility, upside, leverage points, and positive outcomes. "
                    "Be concise, practical, and avoid discussing risks in detail. "
                    "Output plain text in 4-6 short lines."
                ),
            ),
            "risk": DebateAgentConfig(
                role="Risk Analyst Agent",
                temperature=0.35,
                system_prompt=(
                    "You are the Risk Analyst Agent in a structured debate. "
                    "Focus only on risks, constraints, assumptions that may fail, and failure modes. "
                    "Be concise and concrete. Do not propose optimistic arguments. "
                    "Output plain text in 4-6 short lines."
                ),
            ),
            "executor": DebateAgentConfig(
                role="Executor Agent",
                temperature=0.45,
                system_prompt=(
                    "You are the Executor Agent in a structured debate. "
                    "Focus only on technical requirements, implementation path, sequencing, dependencies, "
                    "and operational feasibility. "
                    "Avoid repeating pure risk or pure optimism points. "
                    "Output plain text in 4-6 short lines."
                ),
            ),
            "critic": DebateAgentConfig(
                role="Critic Agent",
                temperature=0.55,
                system_prompt=(
                    "You are the Critic Agent in a structured debate. "
                    "Challenge hidden assumptions, identify logical flaws, and call out weak evidence. "
                    "Do not restate the full risk list; focus on reasoning quality. "
                    "Output plain text in 4-6 short lines."
                ),
            ),
        }

    async def _openrouter_chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int = 500,
    ) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

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
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"OpenRouter malformed response: {exc}") from exc

    async def _infer_with_fallback(
        self,
        *,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int = 500,
    ) -> str:
        try:
            return await self.groq.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as groq_exc:
            logger.warning("Groq failed; using OpenRouter fallback: %s", groq_exc)
            return await self._openrouter_chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    async def run_debate(self, task: str) -> Dict[str, object]:
        task = task.strip()
        if len(task) < 5:
            raise ValueError("Task must contain at least 5 characters")

        prompt = (
            f"User task: {task}\n\n"
            "Analyze this task from your assigned role only. "
            "Use concise, structured bullets with unique reasoning in your role scope."
        )

        responses: Dict[str, str] = {}
        for key, cfg in self.agent_configs.items():
            content = await self._infer_with_fallback(
                system_prompt=cfg.system_prompt,
                user_message=prompt,
                temperature=cfg.temperature,
                max_tokens=420,
            )
            responses[key] = content.strip()
            logger.info("Debate agent response | agent=%s | text=%s", key, responses[key][:400])

        synthesis_system = (
            "You are the Synthesis Module for a multi-agent debate. "
            "Combine four perspectives into one resolved decision. "
            "Rules: resolve conflicts explicitly, do not repeat verbatim, produce concise final decision. "
            "Return JSON only with keys: final_decision, confidence. "
            "confidence must be numeric between 0 and 1."
        )
        synthesis_user = (
            f"Task: {task}\n\n"
            f"Optimist:\n{responses['optimist']}\n\n"
            f"Risk Analyst:\n{responses['risk']}\n\n"
            f"Executor:\n{responses['executor']}\n\n"
            f"Critic:\n{responses['critic']}\n\n"
            "Return JSON now."
        )

        synthesis_raw = await self._infer_with_fallback(
            system_prompt=synthesis_system,
            user_message=synthesis_user,
            temperature=0.25,
            max_tokens=320,
        )

        final_decision = "Insufficient synthesis response"
        confidence = 0.5
        try:
            parsed = json.loads(synthesis_raw)
            final_decision = str(parsed.get("final_decision", final_decision)).strip()
            confidence = float(parsed.get("confidence", confidence))
        except Exception:
            logger.warning("Synthesis JSON parse failed; using plain-text fallback")
            final_decision = synthesis_raw.strip()[:1200] or final_decision

        confidence = max(0.0, min(1.0, confidence))

        return {
            "optimist": responses["optimist"],
            "risk": responses["risk"],
            "executor": responses["executor"],
            "critic": responses["critic"],
            "final_decision": final_decision,
            "confidence": confidence,
        }


_debate_system: Optional[DebateSystem] = None


def get_debate_system() -> DebateSystem:
    global _debate_system
    if _debate_system is None:
        _debate_system = DebateSystem(groq=GroqService())
    return _debate_system
