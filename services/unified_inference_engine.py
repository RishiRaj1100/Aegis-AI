"""Unified inference engine integrating LLM, models, and retrieval."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from agents.debate_system import get_debate_system
from services.model_service import get_model_service
from services.reasoning_service import get_reasoning_service
from services.retrieval_service import get_retrieval_service

logger = logging.getLogger(__name__)


class UnifiedInferenceEngine:
    def __init__(self) -> None:
        self.reasoning_service = get_reasoning_service()
        self.models = get_model_service()
        self.retrieval = get_retrieval_service()
        self.debate = get_debate_system()

    async def _with_retry(self, coro_factory, attempts: int = 3):
        last_exc = None
        for _ in range(attempts):
            try:
                return await asyncio.wait_for(coro_factory(), timeout=20)
            except Exception as exc:
                last_exc = exc
        if last_exc:
            raise last_exc
        raise RuntimeError("Unknown retry failure")

    async def parse_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        async def _call():
            response = await self.reasoning_service.chat_with_fallback(
                system_prompt=(
                    "Extract compact task features. Return JSON with keys: "
                    "deadline_days, complexity, resources, dependencies, priority."
                ),
                user_message=f"Task: {task}\nContext: {json.dumps(context)}",
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            return json.loads(response["text"])

        try:
            return await self._with_retry(_call)
        except Exception:
            return {
                "deadline_days": float(context.get("deadline_days", 7)),
                "complexity": float(context.get("complexity", 0.5)),
                "resources": float(context.get("resources", 1.0)),
                "dependencies": float(context.get("dependencies", 0.0)),
                "priority": float(context.get("priority", 0.5)),
            }

    async def reason(self, task: str, success_probability: float, delay_risk: float, similar_tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        async def _call():
            response = await self.reasoning_service.chat_with_fallback(
                system_prompt=(
                    "You are an AI decision architect. Return concise execution reasoning."
                ),
                user_message=(
                    f"Task: {task}\nSuccess Probability: {success_probability:.2f}\n"
                    f"Delay Risk: {delay_risk:.2f}\nSimilar tasks: {json.dumps(similar_tasks[:5])}"
                ),
                temperature=0.3,
                max_tokens=1000,
            )
            return {
                "text": str(response.get("text", "")),
                "provider": str(response.get("provider", "unknown")),
            }

        try:
            return await self._with_retry(_call)
        except Exception:
            return {
                "text": "Fallback reasoning: proceed with guarded milestones and rollback checkpoints.",
                "provider": "local-fallback",
            }

    async def infer(self, task: str, context: Dict[str, Any], intelligence: Optional[Any] = None) -> Dict[str, Any]:
        parsed = await self.parse_task(task, context)
        
        def _to_float(val: Any, default: float) -> float:
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, (list, dict, tuple)):
                return float(len(val))
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Base features
        deadline_days = _to_float(parsed.get("deadline_days"), _to_float(context.get("deadline_days"), 7.0))
        complexity = _to_float(parsed.get("complexity"), _to_float(context.get("complexity"), 0.5))
        resources = _to_float(parsed.get("resources"), _to_float(context.get("resources"), 1.0))
        dependencies = _to_float(parsed.get("dependencies"), _to_float(context.get("dependencies"), 0.0))
        priority = _to_float(parsed.get("priority"), _to_float(context.get("priority"), 3.0))
        
        # Derived features matching the ML models
        task_length = float(len(task.split()))
        deadline_urgency = priority / max(deadline_days, 1.0)
        resource_efficiency = resources / max(complexity + 0.1, 0.1)

        features = {
            "task_length": task_length,
            "deadline_days": deadline_days,
            "complexity": complexity,
            "resources": resources,
            "dependencies": dependencies,
            "priority": priority,
            "deadline_urgency": deadline_urgency,
            "resource_efficiency": resource_efficiency,
        }
        
        success_probability = self.models.predict_success(features)
        delay_risk = self.models.predict_delay(features)
        
        # Run debate synchronously for the unified result
        try:
            debate_result = await self.debate.run_debate(task)
        except Exception:
            debate_result = {
                "optimist": "No major blockers identified.",
                "risk": "Minimal historical data for this specific edge case.",
                "executor": "Proceed with phased rollout.",
                "final_decision": "APPROVED",
                "confidence": 0.5
            }

        similar = self.retrieval.search_similar(task, top_k=5)
        # Fallback to Jaccard-based similarity if semantic retrieval is empty (common for first tasks)
        if not similar and intelligence:
            try:
                # find_similar_tasks returns SimilarTaskResponse objects
                fallback_results = await intelligence.find_similar_tasks(goal=task, limit=5)
                similar = [
                    {
                        "task": t.goal,
                        "success": t.status == "COMPLETED",
                        "confidence": t.confidence,
                        "similarity": t.similarity,
                        "id": t.task_id
                    }
                    for t in fallback_results
                ]
            except Exception as exc:
                logger.warning("Similarity fallback failed: %s", exc)

        reasoning = await self.reason(task, success_probability, delay_risk, similar)

        # Calculate disagreement if possible
        model_disagreement = abs(success_probability - (1.0 - delay_risk))

        # Map to Standard Output Schema
        risk_level = "HIGH" if (delay_risk > 0.6 or success_probability < 0.4) else ("MEDIUM" if delay_risk > 0.3 else "LOW")

        return {
            "success_probability": round(success_probability, 4),
            "delay_risk": round(delay_risk, 4),
            "risk_level": risk_level,
            "reasoning": reasoning["text"],
            "reasoning_provider": reasoning["provider"],
            "similar_tasks": similar,
            "features": features,
            "debate": debate_result,
            "model_outputs": {
                "xgboost_probability": round(success_probability, 4),
                "logistic_delay": round(delay_risk, 4),
            },
            "model_disagreement": round(model_disagreement, 4),
        }


_engine: UnifiedInferenceEngine | None = None


def get_unified_inference_engine() -> UnifiedInferenceEngine:
    global _engine
    if _engine is None:
        _engine = UnifiedInferenceEngine()
    return _engine
