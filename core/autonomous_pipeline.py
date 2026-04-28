"""Autonomous decision pipeline with full stage tracing."""

from __future__ import annotations

import time
from typing import Any, Dict, List
from uuid import uuid4

from models.autonomous_schemas import AgentIOEnvelope
from services.unified_inference_engine import get_unified_inference_engine


class AutonomousDecisionPipeline:
    def __init__(self, legacy_pipeline: Any) -> None:
        self.legacy = legacy_pipeline
        self.engine = get_unified_inference_engine()

    async def run(self, task: str, language: str, context: Dict[str, Any], user_id: str | None = None) -> Dict[str, Any]:
        traces: List[AgentIOEnvelope] = []

        start = time.perf_counter()
        commander = await self.legacy.commander.decompose(task, context, language)
        traces.append(
            AgentIOEnvelope(
                agent="commander_agent",
                input={"task": task, "language": language, "context": context},
                output={"subtasks": [s.model_dump() for s in commander["subtasks"]], "goal_summary": commander.get("goal_summary", "")},
                latency_ms=(time.perf_counter() - start) * 1000,
            )
        )

        trust_start = time.perf_counter()
        verification = self.legacy.trust.verify_claim(task, context=context, user_id=user_id)
        traces.append(
            AgentIOEnvelope(
                agent="trust_agent",
                input={"task": task, "context": context},
                output={
                    "risk_score": verification.risk_score,
                    "confidence_score": verification.confidence_score,
                    "risk_level": verification.risk_level.value,
                    "reasoning": verification.reasoning,
                    "mitigations": verification.mitigations,
                },
                latency_ms=(time.perf_counter() - trust_start) * 1000,
            )
        )

        infer_start = time.perf_counter()
        inference = await self.engine.infer(task=task, context=context, intelligence=self.legacy.intelligence)
        traces.append(
            AgentIOEnvelope(
                agent="unified_inference_engine",
                input={"task": task, "context": context},
                output=inference,
                latency_ms=(time.perf_counter() - infer_start) * 1000,
            )
        )

        execution_start = time.perf_counter()
        trust_blocked = bool(getattr(verification, "blocking_reason", None)) or verification.risk_score >= 0.8
        if trust_blocked:
            execution_result = {
                "execution_plan": "Execution blocked by trust guardrails until a human override is approved.",
            }
        else:
            execution_result = await self.legacy.executor.generate_plan(
                goal=task,
                goal_summary=commander.get("goal_summary", task),
                subtasks=commander["subtasks"],
                research_insights=inference.get("reasoning", ""),
                risks=verification.mitigations,
                context=context,
                language=language,
            )
        traces.append(
            AgentIOEnvelope(
                agent="execution_agent",
                input={"task": task},
                output={"execution_plan": execution_result.get("execution_plan", "")},
                latency_ms=(time.perf_counter() - execution_start) * 1000,
            )
        )

        reflection_start = time.perf_counter()
        recommendations = list(verification.mitigations[:3])
        if inference["delay_risk"] > 0.65:
            recommendations.append("Reduce delay risk by splitting into smaller milestones.")
        if trust_blocked:
            recommendations.append("Execution blocked until a human override is approved.")

        positive_factors: List[str] = []
        negative_factors: List[str] = []
        if inference["success_probability"] >= 0.7:
            positive_factors.append("Strong success probability from historical model signal.")
        if verification.risk_score <= 0.35:
            positive_factors.append("Trust agent assessed low operational and safety risk.")
        if len(commander["subtasks"]) >= 2:
            positive_factors.append("Task was decomposed into actionable subtasks.")

        if inference["delay_risk"] >= 0.5:
            negative_factors.append("Delay model indicates elevated schedule risk.")
        if verification.risk_score >= 0.6:
            negative_factors.append("Trust verification indicates significant risk factors.")
        if trust_blocked:
            negative_factors.append("Execution is blocked by guardrails pending human approval.")
        traces.append(
            AgentIOEnvelope(
                agent="reflection_agent",
                input={"predicted_success": inference["success_probability"], "delay_risk": inference["delay_risk"]},
                output={"recommendations": recommendations},
                latency_ms=(time.perf_counter() - reflection_start) * 1000,
            )
        )

        task_id = str(uuid4())
        graph = {
            "nodes": [
                {"id": "task", "label": "Task", "type": "task"},
                {"id": "decision", "label": "Decision", "type": "decision"},
                {"id": "reflection", "label": "Reflection", "type": "reflection"},
            ]
            + [
                {"id": f"sub_{idx+1}", "label": s.title, "type": "task"}
                for idx, s in enumerate(commander["subtasks"])
            ],
            "edges": [
                {"source": "task", "target": f"sub_{idx+1}", "label": "decompose"}
                for idx, _ in enumerate(commander["subtasks"])
            ]
            + [
                {"source": f"sub_{idx+1}", "target": "decision", "label": "informs"}
                for idx, _ in enumerate(commander["subtasks"])
            ]
            + [{"source": "decision", "target": "reflection", "label": "learn"}],
        }

        risk_level = "LOW"
        if verification.risk_score >= 0.75 or inference["delay_risk"] >= 0.7:
            risk_level = "HIGH"
        elif verification.risk_score >= 0.45 or inference["delay_risk"] >= 0.45:
            risk_level = "MEDIUM"

        complexity = float(inference.get("features", {}).get("complexity", context.get("complexity", 0.5)) or 0.5)
        complexity = max(complexity, 0.1)
        priority_score = (inference["success_probability"] * (1.0 - inference["delay_risk"])) / complexity
        fallback_used = str(inference.get("reasoning_provider", "")).lower() != "groq"
        model_disagreement = float(inference.get("model_disagreement", 0.0))
        confidence_score = 1.0
        if fallback_used:
            confidence_score -= 0.25
        if model_disagreement >= 0.45:
            confidence_score -= 0.35
        if verification.risk_score >= 0.75:
            confidence_score -= 0.2

        if confidence_score >= 0.75:
            system_confidence = "HIGH"
        elif confidence_score >= 0.45:
            system_confidence = "MEDIUM"
        else:
            system_confidence = "LOW"

        system_trace = [
            {
                "step": "commander",
                "details": {
                    "subtasks": len(commander["subtasks"]),
                    "goal_summary": commander.get("goal_summary", ""),
                },
            },
            {
                "step": "trust",
                "details": {
                    "risk_score": verification.risk_score,
                    "blocked": trust_blocked,
                },
            },
            {
                "step": "retrieval",
                "details": {
                    "matches": len(inference.get("similar_tasks", [])),
                },
            },
            {
                "step": "ml_models",
                "details": {
                    "success": inference["success_probability"],
                    "delay": inference["delay_risk"],
                    "disagreement": model_disagreement,
                },
            },
            {
                "step": "debate",
                "details": {
                    "decision": inference["debate"].get("final_decision", ""),
                },
            },
        ]

        from services.explainability import get_explainability_service
        import pandas as pd

        explainer = get_explainability_service()
        features_df = pd.DataFrame([inference.get("features", {})])
        
        # Ensure we pass the actual model object, not a bundle dict
        success_model = self.engine.models.success_model
        if isinstance(success_model, dict) and "model" in success_model:
            success_model = success_model["model"]

        shap_map, shap_positive, shap_negative = explainer.explain_prediction(
            model=success_model,
            features=features_df
        )

        final = {
            "task_id": task_id,
            "success_probability": inference["success_probability"],
            "delay_risk": inference["delay_risk"],
            "risk_level": risk_level,
            "reasoning": inference["reasoning"],
            "reasoning_provider": inference.get("reasoning_provider"),
            "fallback_used": fallback_used,
            "system_confidence": system_confidence,
            "priority_score": round(priority_score, 4),
            "model_outputs": {
                "xgboost_probability": float(inference.get("model_outputs", {}).get("xgboost_probability", inference["success_probability"])),
                "logistic_delay": float(inference.get("model_outputs", {}).get("logistic_delay", inference["delay_risk"])),
            },
            "similar_tasks": [
                {
                    "task": item.get("task", ""),
                    "outcome": item.get("outcome", "unknown"),
                    "similarity": float(item.get("similarity", 0.0)),
                }
                for item in inference.get("similar_tasks", [])
            ],
            "debate": {
                "optimist": inference["debate"].get("optimist", ""),
                "risk": inference["debate"].get("risk", ""),
                "executor": inference["debate"].get("executor", ""),
                "final_decision": inference["debate"].get("final_decision", ""),
                "confidence": inference["debate"].get("confidence", 0.5),
            },
            "execution_plan": [
                s.title for s in commander["subtasks"]
            ] if not trust_blocked else [],
            "recommendations": recommendations,
            "trust_analysis": {
                "risk_score": verification.risk_score,
                "confidence_score": verification.confidence_score,
                "risk_level": verification.risk_level.value,
                "blocking_reason": verification.blocking_reason,
                "mitigations": verification.mitigations,
            },
            "explainability": {
                "shap_values": shap_map,
                "positive_factors": positive_factors + shap_positive,
                "negative_factors": negative_factors + shap_negative,
            },
            "execution_graph": graph,
            "system_trace": system_trace,
            "traces": [trace.model_dump() for trace in traces],
        }

        return final
