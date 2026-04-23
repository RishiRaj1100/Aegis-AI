"""
AegisAI - Trust Agent
Performs a holistic LLM-driven confidence and risk assessment that considers
the full context of a goal: its complexity, research quality, execution
feasibility, historical success signals, identified risks, and time/resource
constraints.

No rigid formula is used. The LLM reasons over all available evidence and
returns calibrated scores for six intuitive dimensions, a composite confidence
score (0-100), and a clear plain-language explanation suited to the user's
language.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from services.groq_service import GroqService
from models.schemas import RiskLevel, TrustComponents, TrustScore
from config.settings import get_settings
from utils.helpers import language_instruction

logger = logging.getLogger(__name__)
settings = get_settings()

_WEIGHTS = {
    "goal_clarity": settings.TRUST_WEIGHT_GOAL_CLARITY,
    "information_quality": settings.TRUST_WEIGHT_INFORMATION_QUALITY,
    "execution_feasibility": settings.TRUST_WEIGHT_EXECUTION_FEASIBILITY,
    "risk_manageability": settings.TRUST_WEIGHT_RISK_MANAGEABILITY,
    "resource_adequacy": settings.TRUST_WEIGHT_RESOURCE_ADEQUACY,
    "external_uncertainty": settings.TRUST_WEIGHT_EXTERNAL_UNCERTAINTY,
}

# ── System prompt ─────────────────────────────────────────────────────────────

def _build_trust_prompt() -> str:
    return f"""
You are the Trust Agent of AegisAI — a senior risk analyst and confidence assessor.

Your job is to evaluate how confident AegisAI is in the success of the user's goal,
given everything the other agents have produced. You must think holistically — every
goal is different, every situation is unique.

Evaluate six dimensions, score each 0.0 to 1.0:

1. goal_clarity          — How clearly and specifically has the goal been defined?
                           (vague wishful thinking = 0.1, crisp measurable objective = 1.0)
2. information_quality   — How complete, relevant, and reliable is the research gathered?
                           (almost no data = 0.1, rich, well-sourced intelligence = 1.0)
3. execution_feasibility — How realistic is it to carry out the execution plan given real-world
                           constraints (time, budget, team, technology, market)?
                           (highly unrealistic = 0.1, straightforward with clear steps = 1.0)
4. risk_manageability    — How controllable are the identified risks?
                           (existential uncontrollable risks = 0.1, minor manageable risks = 1.0)
5. resource_adequacy     — Are the available resources (time, capital, people, tools) sufficient?
                           (severely under-resourced = 0.1, well-resourced and realistic = 1.0)
6. external_uncertainty  — How stable and predictable is the environment around this goal?
                           (high market/regulatory/technical uncertainty = 0.1, stable = 1.0)

Then compute:
  confidence_score = round(
        goal_clarity * {_WEIGHTS['goal_clarity']:.2f} +
        information_quality * {_WEIGHTS['information_quality']:.2f} +
        execution_feasibility * {_WEIGHTS['execution_feasibility']:.2f} +
        risk_manageability * {_WEIGHTS['risk_manageability']:.2f} +
        resource_adequacy * {_WEIGHTS['resource_adequacy']:.2f} +
        external_uncertainty * {_WEIGHTS['external_uncertainty']:.2f}
  , 1) * 100   [result must be 0–100]

Risk level:
    - HIGH   if confidence_score < {settings.RISK_HIGH_THRESHOLD:.1f}
    - MEDIUM if confidence_score < {settings.RISK_MEDIUM_THRESHOLD:.1f}
    - LOW    if confidence_score >= {settings.RISK_MEDIUM_THRESHOLD:.1f}

Return a valid JSON object — nothing else:
{{
  "goal_clarity": <0.0-1.0>,
  "information_quality": <0.0-1.0>,
  "execution_feasibility": <0.0-1.0>,
  "risk_manageability": <0.0-1.0>,
  "resource_adequacy": <0.0-1.0>,
  "external_uncertainty": <0.0-1.0>,
  "confidence_score": <0.0-100.0>,
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "reasoning": "<3-5 sentence plain-language explanation of WHY this score was given, what the key limiting factor is, and one concrete improvement action>",
  "improvement_tip": "<one specific actionable improvement>"
}}
""".strip()


_TRUST_PROMPT = _build_trust_prompt()


class TrustAgent:
    """
    Performs a holistic, LLM-driven confidence and risk assessment.

    Replaces the previous rigid weighted formula with a contextual evaluation
    that adapts to every goal scenario.
    """

    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    # ── Public API ────────────────────────────────────────────────────────────

    async def evaluate(
        self,
        past_success_rate: float,
        data_completeness: float,
        task_feasibility: float,
        complexity_score: float,
        goal: str,
        goal_summary: str,
        language: str = "en-IN",
        research_insights: str = "",
        execution_plan: str = "",
        risks: list | None = None,
        context: Dict[str, Any] | None = None,
    ) -> TrustScore:
        """
        Holistic LLM-driven confidence and risk evaluation.

        Returns:
            TrustScore with confidence, risk_level, components, reasoning.
        """
        risks_text = "\n".join(f"  - {r}" for r in (risks or [])) or "  None explicitly identified."
        context_text = ""
        if context:
            context_text = "\nUser-provided context: " + ", ".join(f"{k}={v}" for k, v in context.items())

        lang_note = language_instruction(language)

        user_message = (
            f"GOAL: {goal}\n"
            f"REFINED SUMMARY: {goal_summary}\n\n"
            f"RESEARCH INSIGHTS (excerpt):\n{research_insights[:1000]}\n\n"
            f"EXECUTION PLAN (excerpt):\n{execution_plan[:800]}\n\n"
            f"IDENTIFIED RISKS:\n{risks_text}\n\n"
            f"HISTORICAL SUCCESS RATE (similar past tasks): {past_success_rate:.0%}\n"
            f"RESEARCH DATA COMPLETENESS: {data_completeness:.0%}\n"
            f"RAW TASK FEASIBILITY (from Research Agent): {task_feasibility:.0%}\n"
            f"COMPLEXITY SCORE (from Commander): {complexity_score:.2f} / 1.0"
            f"{context_text}"
        )
        if lang_note:
            user_message += lang_note

        logger.info("Trust Agent running holistic LLM evaluation…")
        raw: Dict[str, Any] = await self.groq.chat_json(
            system_prompt=_TRUST_PROMPT,
            user_message=user_message,
            temperature=0.3,
            max_tokens=1500,  # 6 scores + reasoning paragraph + JSON
        )

        # Extract and clamp all dimension scores
        def _clamp(v: Any, lo: float = 0.0, hi: float = 1.0) -> float:
            try:
                return max(lo, min(hi, float(v)))
            except (TypeError, ValueError):
                return 0.5

        gc  = _clamp(raw.get("goal_clarity", 0.5))
        iq  = _clamp(raw.get("information_quality", data_completeness))
        ef  = _clamp(raw.get("execution_feasibility", task_feasibility))
        rm  = _clamp(raw.get("risk_manageability", 0.5))
        ra  = _clamp(raw.get("resource_adequacy", 0.5))
        eu  = _clamp(raw.get("external_uncertainty", 0.5))

        # Use LLM-computed confidence; fall back to weighted formula if needed
        raw_conf = raw.get("confidence_score")
        if raw_conf is not None:
            confidence = round(max(0.0, min(100.0, float(raw_conf))), 1)
        else:
            confidence = round(
                (
                    gc * _WEIGHTS["goal_clarity"]
                    + iq * _WEIGHTS["information_quality"]
                    + ef * _WEIGHTS["execution_feasibility"]
                    + rm * _WEIGHTS["risk_manageability"]
                    + ra * _WEIGHTS["resource_adequacy"]
                    + eu * _WEIGHTS["external_uncertainty"]
                )
                * 100,
                1,
            )

        # Risk level from LLM; fall back to threshold rules
        raw_risk = str(raw.get("risk_level", "")).upper()
        if raw_risk in {"LOW", "MEDIUM", "HIGH"}:
            risk_level = RiskLevel(raw_risk)
        else:
            risk_level = self._compute_risk(confidence)

        # Pack into TrustComponents using the six new dimensions
        components = TrustComponents(
            goal_clarity=gc,
            information_quality=iq,
            execution_feasibility=ef,
            risk_manageability=rm,
            resource_adequacy=ra,
            external_uncertainty=eu,
        )

        reasoning = raw.get("reasoning", "Holistic trust analysis completed.")
        tip = raw.get("improvement_tip", "")
        if tip:
            reasoning += f"\n\n**Key Action:** {tip}"

        logger.info(
            "Trust Agent | confidence=%.1f%% | risk=%s | gc=%.2f iq=%.2f ef=%.2f rm=%.2f ra=%.2f eu=%.2f",
            confidence, risk_level.value, gc, iq, ef, rm, ra, eu,
        )

        return TrustScore(
            confidence=confidence,
            risk_level=risk_level,
            components=components,
            reasoning=reasoning,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_risk(self, confidence: float) -> RiskLevel:
        if confidence < settings.RISK_HIGH_THRESHOLD:
            return RiskLevel.HIGH
        if confidence < settings.RISK_MEDIUM_THRESHOLD:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
