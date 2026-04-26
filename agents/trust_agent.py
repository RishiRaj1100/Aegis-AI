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
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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

Your job is to perform claim extraction, risk scoring, and a 6-dimensional trust evaluation for the user's goal and research insights.

Evaluate these six dimensions (0.0 to 1.0):
1. goal_clarity: How clear and specific the goal is.
2. information_quality: Completeness and reliability of available data.
3. execution_feasibility: Real-world achievability.
4. risk_manageability: How controllable the identified risks are.
5. resource_adequacy: Sufficiency of time and resources.
6. external_uncertainty: Stability of the environment.

Identify the core assumptions (claims) and potential failure scenarios.

Return a valid JSON object matching this schema — nothing else:
{{
  "claims": ["<extracted claim 1>", "<extracted claim 2>"],
  "confidence_score": <0.0 to 1.0>,
  "delay_risk": <0.0 to 1.0 (estimated probability of missing deadlines)>,
  "failure_scenarios": ["<scenario 1>", "<scenario 2>"],
  "dimensions": {{
    "goal_clarity": <score>,
    "information_quality": <score>,
    "execution_feasibility": <score>,
    "risk_manageability": <score>,
    "resource_adequacy": <score>,
    "external_uncertainty": <score>
  }}
}}
""".strip()

_TRUST_PROMPT = _build_trust_prompt()

@dataclass(slots=True)
class VerificationResult:
    claim: str
    is_verified: bool
    risk_score: float
    confidence_score: float
    risk_level: RiskLevel
    evidence: List[Dict[str, Any]]
    reasoning: str
    mitigations: List[str]
    blocking_reason: Optional[str]
    timestamp: str


class TrustAgent:
    """
    Performs claim extraction, risk scoring, and failure scenario identification.
    """

    def __init__(self, groq: GroqService | None = None, db: Any | None = None, search_service: Any | None = None) -> None:
        self.groq = groq
        self.db = db
        self.search_service = search_service

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
        risks: list | None = None,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Holistic LLM-driven confidence and risk evaluation.
        Returns a dict matching the trust_analysis schema.
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
            f"IDENTIFIED RISKS:\n{risks_text}\n\n"
            f"{context_text}\n\n"
            "Analyze these inputs and return the JSON with claims, confidence_score, failure_scenarios, and the 6 trust dimensions."
        )
        if lang_note:
            user_message += lang_note

        logger.info("Trust Agent running 6D evaluation and claim extraction…")
        try:
            raw: Dict[str, Any] = await self.groq.chat_json(
                system_prompt=_TRUST_PROMPT,
                user_message=user_message,
                temperature=0.2,
            )
            
            dims = raw.get("dimensions", {})
            return {
                "claims": raw.get("claims", []),
                "confidence_score": float(raw.get("confidence_score", 0.5)),
                "delay_risk": float(raw.get("delay_risk", 0.3)),
                "failure_scenarios": raw.get("failure_scenarios", []),
                "dimensions": {
                    "goal_clarity": float(dims.get("goal_clarity", 0.5)),
                    "information_quality": float(dims.get("information_quality", 0.5)),
                    "execution_feasibility": float(dims.get("execution_feasibility", 0.5)),
                    "risk_manageability": float(dims.get("risk_manageability", 0.5)),
                    "resource_adequacy": float(dims.get("resource_adequacy", 0.5)),
                    "external_uncertainty": float(dims.get("external_uncertainty", 0.5)),
                }
            }
        except Exception as exc:
            logger.error("Trust Agent evaluation failed: %s", exc)
            return {
                "claims": ["Assumes plan is executable without detailed constraints."],
                "confidence_score": 0.5,
                "delay_risk": 0.4,
                "failure_scenarios": ["Unforeseen technical blockers.", "Resource unavailability."],
                "dimensions": {
                    "goal_clarity": 0.5,
                    "information_quality": 0.5,
                    "execution_feasibility": 0.5,
                    "risk_manageability": 0.5,
                    "resource_adequacy": 0.5,
                    "external_uncertainty": 0.5,
                }
            }


    async def verify_claim(
        self,
        claim: str,
        context: Dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> VerificationResult:
        """Verify a claim using local evidence and historical similarity."""
        claim_factors = self._extract_claim_factors(claim, context)
        similar_cases = await self._retrieve_similar_cases(claim, context=context, user_id=user_id)
        risk_score, evidence = self._compute_risk_score(claim_factors, similar_cases)
        confidence_score = self._compute_confidence(evidence, similar_cases, risk_score)
        risk_level = self._get_risk_level(risk_score)
        mitigations = self._suggest_mitigations(claim_factors, risk_level, similar_cases)
        reasoning = self._generate_reasoning(claim, evidence, risk_level)

        blocking_reason: Optional[str] = None
        if risk_score > 0.85:
            blocking_reason = f"Critical risk ({risk_score:.2f}). Operation blocked."
        elif confidence_score < 0.3:
            blocking_reason = f"Insufficient confidence ({confidence_score:.2f}). Human review required."

        is_verified = blocking_reason is None and risk_score <= 0.65 and confidence_score >= 0.45
        result = VerificationResult(
            claim=claim,
            is_verified=is_verified,
            risk_score=round(max(0.0, min(1.0, risk_score)), 3),
            confidence_score=round(max(0.0, min(1.0, confidence_score)), 3),
            risk_level=risk_level,
            evidence=evidence,
            reasoning=reasoning,
            mitigations=mitigations,
            blocking_reason=blocking_reason,
            timestamp=datetime.utcnow().isoformat(),
        )

        self._store_verification(result, user_id, context)
        return result

    def should_block_execution(self, verification: VerificationResult) -> bool:
        """Return True when execution should be blocked by policy gates."""
        return (
            verification.risk_score > 0.8
            or verification.confidence_score < 0.4
            or not verification.is_verified
        )

    def _extract_claim_factors(self, claim: str, context: Dict[str, Any] | None) -> Dict[str, Any]:
        factors: Dict[str, Any] = {}
        lowered = claim.lower()

        if match := re.search(r"(\d+)\s*hours?", lowered):
            factors["estimated_duration_hours"] = int(match.group(1))
        if match := re.search(r"(\d+)\s*days?", lowered):
            factors["estimated_duration_days"] = int(match.group(1))

        if any(term in lowered for term in ["high priority", "urgent", "critical"]):
            factors["priority"] = "high"
        elif any(term in lowered for term in ["low priority", "backlog"]):
            factors["priority"] = "low"

        if any(term in lowered for term in ["team", "resource", "dependency", "integration"]):
            factors["has_team_dependency"] = True

        if context:
            for key, value in context.items():
                factors[key] = value

        return factors

    def _get_tasks_collection(self):
        if self.db is not None:
            return self.db["tasks"]
        try:
            from services.mongodb_service import get_db

            return get_db()["tasks"]
        except Exception:
            return None

    async def _retrieve_similar_cases(
        self,
        claim: str,
        context: Dict[str, Any] | None = None,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical cases to verify the current claim."""
        if self.search_service and hasattr(self.search_service, "find_similar_tasks"):
            try:
                results = await self.search_service.find_similar_tasks(
                    goal=claim,
                    user_id=user_id,
                    limit=top_k
                )
                return [
                    {
                        "case_id": r.task_id,
                        "status": r.status,
                        "similarity": r.similarity,
                        "confidence": r.confidence
                    } for r in results
                ]
            except Exception as e:
                logger.warning(f"Trust search failed: {e}")
        return []

    def _compute_risk_score(
        self,
        claim_factors: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        evidence: List[Dict[str, Any]] = []
        if not similar_cases:
            base_risk = 0.55
            evidence.append({"type": "no_similar_cases", "weight": 0.0})
        else:
            weighted_failure = 0.0
            weighted_total = 0.0
            for case in similar_cases:
                similarity = float(case.get("similarity", 0.0))
                weighted_total += similarity
                status = str(case.get("status", "UNKNOWN"))
                if status == "FAILED":
                    weighted_failure += similarity
                    evidence.append(
                        {
                            "type": "similar_failure",
                            "case_id": case.get("case_id"),
                            "similarity": similarity,
                            "weight": -1.0,
                        }
                    )
                elif status == "COMPLETED":
                    evidence.append(
                        {
                            "type": "similar_success",
                            "case_id": case.get("case_id"),
                            "similarity": similarity,
                            "weight": 1.0,
                        }
                    )

            if weighted_total > 0:
                base_risk = weighted_failure / weighted_total
            else:
                base_risk = 0.5

        duration_days = float(claim_factors.get("estimated_duration_days", 0) or 0)
        duration_hours = float(claim_factors.get("estimated_duration_hours", 0) or 0)
        if duration_days > 30:
            base_risk += 0.12
            evidence.append({"type": "long_duration", "weight": 0.12, "value": duration_days})
        if duration_hours > 40:
            base_risk += 0.08
            evidence.append({"type": "long_duration", "weight": 0.08, "value": duration_hours})

        if claim_factors.get("has_team_dependency"):
            base_risk += 0.05
            evidence.append({"type": "dependency_pressure", "weight": 0.05})

        if str(claim_factors.get("priority", "")).lower() == "high":
            base_risk += 0.05
            evidence.append({"type": "priority_pressure", "weight": 0.05})

        return max(0.0, min(1.0, base_risk)), evidence

    def _compute_confidence(
        self,
        evidence: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]],
        risk_score: float,
    ) -> float:
        if not evidence and not similar_cases:
            # Baseline confidence for valid-sounding goals when no history exists
            return max(0.4, 0.72 - risk_score)

        avg_similarity = sum(float(case.get("similarity", 0.0)) for case in similar_cases) / len(similar_cases) if similar_cases else 0.0
        evidence_strength = min(1.0, 0.2 + (len(evidence) * 0.08) + (avg_similarity * 0.45))
        confidence = evidence_strength * 0.6 + (1.0 - risk_score) * 0.4
        return max(0.0, min(1.0, confidence))

    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        if risk_score >= 0.8:
            return RiskLevel.HIGH
        if risk_score >= 0.45:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _suggest_mitigations(
        self,
        claim_factors: Dict[str, Any],
        risk_level: RiskLevel,
        similar_cases: List[Dict[str, Any]],
    ) -> List[str]:
        mitigations: List[str] = []
        if risk_level == RiskLevel.HIGH:
            mitigations.append("Split the claim into smaller verifiable steps before execution.")
        if claim_factors.get("has_team_dependency"):
            mitigations.append("Validate dependencies and ownership before proceeding.")
        if claim_factors.get("priority") == "high":
            mitigations.append("Add a human approval gate because the task is time-sensitive.")
        if similar_cases:
            failed = sum(1 for case in similar_cases if case.get("status") == "FAILED")
            if failed:
                mitigations.append("Review the failure modes from the closest historical cases.")
        if not mitigations:
            mitigations.append("Proceed with monitoring and record the outcome for calibration.")
        return mitigations

    def _generate_reasoning(self, claim: str, evidence: List[Dict[str, Any]], risk_level: RiskLevel) -> str:
        evidence_count = len(evidence)
        if evidence_count == 0:
            return (
                f"The claim '{claim}' could not be matched against strong historical evidence, so the assessment stays conservative. "
                f"Current risk is {risk_level.value.lower()} because the system has limited comparable cases."
            )
        failures = sum(1 for item in evidence if item.get("type") == "similar_failure")
        successes = sum(1 for item in evidence if item.get("type") == "similar_success")
        return (
            f"The claim '{claim}' was evaluated against {evidence_count} evidence signals, including {successes} similar successes and {failures} similar failures. "
            f"The resulting risk level is {risk_level.value.lower()} because the closest historical cases were used as the primary signal."
        )

    def _store_verification(self, result: VerificationResult, user_id: str | None, context: Dict[str, Any] | None) -> None:
        collection = None
        try:
            if self.db is not None:
                collection = self.db["verifications"]
            else:
                from services.mongodb_service import get_db

                collection = get_db()["verifications"]
        except Exception:
            return

        if collection is None:
            return

        try:
            collection.create_index("timestamp")
            collection.create_index("is_verified")
            collection.insert_one(
                {
                    "claim": result.claim,
                    "is_verified": result.is_verified,
                    "risk_score": result.risk_score,
                    "confidence_score": result.confidence_score,
                    "risk_level": result.risk_level.value,
                    "evidence": result.evidence,
                    "reasoning": result.reasoning,
                    "mitigations": result.mitigations,
                    "blocking_reason": result.blocking_reason,
                    "timestamp": datetime.utcnow(),
                    "user_id": user_id,
                    "context": context or {},
                }
            )
        except Exception as exc:
            logger.warning("Trust Agent verification persistence failed: %s", exc)


def get_trust_agent(groq: GroqService | None = None, db: Any | None = None, search_service: Any | None = None) -> TrustAgent:
    """Return a singleton trust agent used by compatibility routers."""
    global _TRUST_AGENT_SINGLETON
    try:
        _TRUST_AGENT_SINGLETON
    except NameError:
        _TRUST_AGENT_SINGLETON = None

    if _TRUST_AGENT_SINGLETON is None:
        _TRUST_AGENT_SINGLETON = TrustAgent(groq=groq, db=db, search_service=search_service)
    return _TRUST_AGENT_SINGLETON

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _compute_risk(self, confidence: float) -> RiskLevel:
        if confidence < settings.RISK_HIGH_THRESHOLD:
            return RiskLevel.HIGH
        if confidence < settings.RISK_MEDIUM_THRESHOLD:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
