"""
AegisAI - Research Agent
Gathers contextual insights, feasibility signals, and domain knowledge
for a given goal + subtask list using the Groq LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from services.groq_service import GroqService
from models.schemas import SubTask
from utils.helpers import language_instruction

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
CRITICAL RULES:
- GROUNDING: Base all insights and risks strictly on verifiable domain knowledge. 
- ANTI-HALLUCINATION: Do NOT invent fake URLs, software versions, or specific technical details if you are not 100% certain. If unsure, use placeholders like "[Source verification required]".
- SPECIFICITY: Insights must be ≥ 100 words and include concrete, actionable observations specific to the goal.
- RESOURCES: Only recommend resources (URLs/references) that are well-known and relevant.

Return a valid JSON object:
{
  "insights": "<detailed narrative>",
  "data_completeness": <0.0–1.0>,
  "task_feasibility": <0.0–1.0>,
  "risks": ["<risk 1>", ...],
  "opportunities": ["<opportunity 1>", ...],
  "recommended_resources": ["<URL or reference>", ...]
}
""".strip()


class ResearchAgent:
    """
    Produces contextual insights, feasibility and data-completeness scores
    for the Commander's decomposed plan.
    """

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    async def research(
        self,
        goal: str,
        goal_summary: str,
        subtasks: List[SubTask],
        context: Dict[str, Any] | None = None,
        language: str = "en-IN",
    ) -> Dict[str, Any]:
        """
        Run research on the goal and its subtasks.

        Returns:
            Dict containing: insights (str), data_completeness (float),
            task_feasibility (float), risks, opportunities, recommended_resources.
        """
        subtask_text = "\n".join(
            f"  [{s.id}] {s.title}: {s.description}" for s in subtasks
        )
        context_str = ""
        if context:
            context_str = "\nContext: " + ", ".join(f"{k}={v}" for k, v in context.items())

        user_message = (
            f"Original Goal: {goal}\n"
            f"Refined Summary: {goal_summary}\n"
            f"Subtasks:\n{subtask_text}"
            f"{context_str}"
        )
        lang_note = language_instruction(language)
        if lang_note:
            user_message += lang_note

        logger.info("Research Agent analysing goal (subtasks=%d) …", len(subtasks))
        raw: Dict[str, Any] = await self.groq.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.3,
            max_tokens=2048,  # insights paragraph + JSON overhead
        )

        result = {
            "insights": raw.get("insights", "No insights available."),
            "data_completeness": max(0.0, min(1.0, float(raw.get("data_completeness", 0.5)))),
            "task_feasibility": max(0.0, min(1.0, float(raw.get("task_feasibility", 0.5)))),
            "risks": raw.get("risks", []),
            "opportunities": raw.get("opportunities", []),
            "recommended_resources": raw.get("recommended_resources", []),
        }
        logger.info(
            "Research Agent done | completeness=%.2f | feasibility=%.2f",
            result["data_completeness"],
            result["task_feasibility"],
        )
        return result
