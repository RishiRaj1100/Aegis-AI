"""
AegisAI - Commander Agent
Receives a user goal and decomposes it into an ordered list of subtasks,
each with title, description, priority, estimated duration, and dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.groq_service import GroqService
from models.schemas import SubTask
from utils.helpers import language_instruction

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are the Commander Agent of AegisAI — a precision goal decomposition engine.

Your role:
  1. Carefully analyse the user's goal. Identify if it is technical, creative, physical, or conceptual.
  2. Break it into a minimum of 3 and maximum of 10 concrete, actionable subtasks.
  3. Decompose into strictly ordered linear steps. Each step MUST have a clear input and output.
  4. Each subtask must be completable in isolation after its dependencies are met.
  5. Assign a priority (1 = highest, 5 = lowest) and estimated duration in minutes.
  6. Identify dependency IDs so the execution graph is unambiguous.

CRITICAL RULES:
- GROUNDING: Base subtasks ONLY on the user's goal and context. Do not invent features or requirements the user did not ask for.
- HALLUCINATION: If a goal is impossible, do not "pretend" it is possible. Instead, create subtasks that research the constraints or explain the impossibility.
- NO GENERIC TASKS: Do not use tasks like 'research' or 'prepare'. Subtasks must produce a tangible artifact or state change.
- SANITY CHECK: Do not default to software deployment templates unless the goal is specifically about software.

Output a valid JSON object with this schema:
{
  "subtasks": [
    {
      "id": "<id>",
      "title": "<title>",
      "description": "<desc>",
      "priority": <1-5>,
      "estimated_duration_minutes": <int>,
      "dependencies": ["<id>"]
    }
  ],
  "goal_summary": "<summary>",
  "complexity_score": <0.0-1.0>
}
""".strip()


class CommanderAgent:
    """
    Decomposes a high-level user goal into an actionable subtask graph.

    Attributes:
        groq (GroqService): Shared LLM client.
    """

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    async def decompose(
        self,
        goal: str,
        context: Dict[str, Any] | None = None,
        language: str = "en-IN",
    ) -> Dict[str, Any]:
        """
        Decompose `goal` into subtasks.

        Args:
            goal      : Raw user goal string.
            context   : Optional KV context (e.g. budget, team_size).
            language  : BCP-47 language tag of the goal text.

        Returns:
            Dict with keys: subtasks (List[SubTask]), goal_summary, complexity_score.
        """
        context_str = ""
        if context:
            context_str = "\n\nAdditional context provided by user:\n" + "\n".join(
                f"  {k}: {v}" for k, v in context.items()
            )

        user_message = f"Goal: {goal}{context_str}"
        lang_note = language_instruction(language)
        if lang_note:
            user_message += lang_note
        elif language != "en-IN":
            user_message += f"\n\n[Goal language: '{language}'.]"

        logger.info("Commander Agent decomposing goal (len=%d) …", len(goal))
        raw: Dict[str, Any] = await self.groq.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.2,
            max_tokens=1500,  # subtask JSON is compact — no need for 4096+
        )

        subtasks_raw: List[Dict[str, Any]] = raw.get("subtasks", [])
        goal_summary: str = raw.get("goal_summary", goal[:120])
        complexity_score: float = float(raw.get("complexity_score", 0.5))

        # Validate + coerce into SubTask models
        subtasks: List[SubTask] = []
        for st in subtasks_raw:
            try:
                subtasks.append(SubTask(**st))
            except Exception as exc:
                logger.warning("Subtask coercion failed: %s | raw=%s", exc, st)

        logger.info("Commander Agent produced %d subtasks | complexity=%.2f", len(subtasks), complexity_score)

        return {
            "subtasks": subtasks,
            "goal_summary": goal_summary,
            "complexity_score": complexity_score,
        }
