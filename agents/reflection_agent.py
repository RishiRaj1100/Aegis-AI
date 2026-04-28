"""
AegisAI - Reflection Agent
Analyses past task outcomes to update confidence logic,
surface patterns, and generate actionable lessons for future executions.
The agent stores a ReflectionDocument in MongoDB after each analysis cycle.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from services.groq_service import GroqService
from agents.memory_agent import MemoryAgent
from models.schemas import ReflectionDocument

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
You are the Reflection Agent of AegisAI — a meta-learning strategist and continuous improvement engine.

Your role:
  1. Review the outcomes of recent tasks (completed or failed) with their confidence scores.
  2. Identify patterns — what types of goals succeed, which fail, and why.
  3. Derive calibration adjustments: should the trust formula weights be nudged?
  4. Generate concrete lessons to improve future planning and confidence scoring.

Return a valid JSON object:
{
  "lessons": ["<lesson 1>", "<lesson 2>", ...],
  "pattern_summary": "<paragraph describing patterns observed>",
  "confidence_calibration_note": "<recommendation on whether confidence scoring is over/under-estimated>",
  "suggested_weight_adjustments": {
        "goal_clarity": <-0.05 to 0.05>,
        "information_quality": <-0.05 to 0.05>,
        "execution_feasibility": <-0.05 to 0.05>,
        "risk_manageability": <-0.05 to 0.05>,
        "resource_adequacy": <-0.05 to 0.05>,
        "external_uncertainty": <-0.05 to 0.05>
  },
  "updated_confidence_bias": <-5.0 to 5.0>
}

Rules:
- lessons must be specific and actionable.
- suggested_weight_adjustments values must be small increments (will not be auto-applied — advisory only).
- Return ONLY valid JSON.
""".strip()


class ReflectionAgent:
    """
    Runs periodic reflection cycles over historical task outcomes.

    Actions:
      1. Fetch recent task history from MemoryAgent.
      2. Send to Groq for pattern analysis and lesson extraction.
      3. Run optional per-task reflection when a task outcome is recorded.
      4. Persist reflection documents via MemoryAgent.
    """

    def __init__(self, groq: GroqService, memory: MemoryAgent) -> None:
        self.groq = groq
        self.memory = memory

    # ── Global reflection (periodic) ─────────────────────────────────────────

    async def run_global_reflection(self, sample_size: int = 20) -> Dict[str, Any]:
        """
        Analyse the last `sample_size` tasks and produce a global reflection report.

        Returns:
            Dict with keys: lessons, pattern_summary, confidence_calibration_note,
            suggested_weight_adjustments, updated_confidence_bias.
        """
        recent_tasks = await self.memory.get_recent_tasks(limit=sample_size)

        if not recent_tasks:
            logger.info("Reflection Agent: no tasks to reflect on.")
            return {"lessons": [], "pattern_summary": "No task history available yet."}

        task_summaries = self._format_task_summaries(recent_tasks)
        user_message = f"Recent task outcomes ({len(recent_tasks)} tasks):\n\n{task_summaries}"

        logger.info("Reflection Agent running global reflection on %d tasks …", len(recent_tasks))
        raw: Dict[str, Any] = await self.groq.chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.35,
            max_tokens=1200,  # lessons list + summary + weight adjustments JSON
        )

        result = {
            "lessons": raw.get("lessons", []),
            "pattern_summary": raw.get("pattern_summary", ""),
            "confidence_calibration_note": raw.get("confidence_calibration_note", ""),
            "suggested_weight_adjustments": raw.get("suggested_weight_adjustments", {}),
            "updated_confidence_bias": float(raw.get("updated_confidence_bias", 0.0)),
        }
        logger.info(
            "Reflection Agent global reflection done | lessons=%d",
            len(result["lessons"]),
        )
        return result

    # ── Per-task reflection ───────────────────────────────────────────────────

    async def reflect_on_task(
        self,
        task_id: str,
        previous_confidence: float,
        outcome_status: str,
        outcome_notes: str | None = None,
    ) -> str:
        """
        Reflect on a single completed/failed task and store a ReflectionDocument.

        Returns:
            The reflection_id of the stored document.
        """
        task_doc = await self.memory.get_task(task_id)
        if not task_doc:
            logger.warning("Reflection Agent: task %s not found.", task_id)
            return ""

        # Estimate updated confidence based on outcome
        if outcome_status == "COMPLETED":
            updated_confidence = min(100.0, previous_confidence + 5.0)
            lesson = (
                f"Task '{task_doc.get('goal', '')[:80]}' was COMPLETED successfully. "
                f"Confidence should trend upward for similar tasks."
            )
        else:
            updated_confidence = max(0.0, previous_confidence - 10.0)
            lesson = (
                f"Task '{task_doc.get('goal', '')[:80]}' FAILED. "
                f"Confidence should trend downward for similar tasks. "
                f"Notes: {outcome_notes or 'none provided'}."
            )

        reflection = ReflectionDocument(
            reflection_id=str(uuid4()),
            task_id=task_id,
            previous_confidence=previous_confidence,
            updated_confidence=updated_confidence,
            lesson=lesson,
            created_at=datetime.utcnow(),
        )

        reflection_id = await self.memory.save_reflection(reflection.model_dump())
        logger.info(
            "Reflection Agent: reflection %s stored for task %s | conf %.1f → %.1f",
            reflection_id,
            task_id,
            previous_confidence,
            updated_confidence,
        )
        return reflection_id

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _format_task_summaries(self, tasks: List[Dict[str, Any]]) -> str:
        lines: List[str] = []
        for t in tasks:
            goal_snippet = str(t.get("goal", ""))[:80]
            confidence = t.get("confidence", "?")
            status = t.get("status", "UNKNOWN")
            risk = t.get("risk_level", "?")
            duration = t.get("actual_duration_minutes", "?")
            lines.append(
                f"• [{status}] conf={confidence}% | risk={risk} | "
                f"duration={duration}min | goal=\"{goal_snippet}\""
            )
        return "\n".join(lines)

    async def reflect(
        self,
        task_id: str,
        goal: str,
        confidence: float,
        risk_level: str,
        debate_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Live reflection for the pipeline.
        Compares current prediction against similar historical tasks.
        """
        try:
            # 1. Fetch similar historical tasks to compare against
            similar = await self.memory.get_recent_tasks(limit=3)
            
            past_avg = 0.0
            if similar:
                past_avg = sum(t.get("confidence", 50.0) for t in similar) / len(similar)
            else:
                past_avg = confidence * 0.9 # Default fallback

            # 2. Extract insights from debate
            consensus = debate_results.get("consensus_score", 0.7)
            
            # 3. Generate reflection insights
            insights = []
            if confidence > past_avg:
                insights.append(f"Current goal complexity is lower than historical benchmarks.")
            else:
                insights.append(f"Goal specifications are more stringent than previous successful missions.")
                
            if consensus < 0.6:
                insights.append("Debate agents surfaced significant conflicting risks.")
            else:
                insights.append("High alignment across specialized reasoning nodes.")

            return {
                "past_prediction": past_avg,
                "current_prediction": confidence,
                "improvement_delta": confidence - past_avg,
                "insights": insights
            }
        except Exception as e:
            logger.error(f"Reflection failure: {e}")
            return {
                "past_prediction": confidence * 0.95,
                "current_prediction": confidence,
                "improvement_delta": confidence * 0.05,
                "insights": ["Heuristic reflection baseline applied."]
            }
