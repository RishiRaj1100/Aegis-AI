"""
AegisAI - Intelligence Service
Heuristic execution intelligence layer for graphing, similarity search,
prediction, simulation, registry management, and scheduled reflection reports.
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

try:
    import joblib
    import pandas as pd
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from config.settings import get_settings
from models.schemas import (
    DriftReportResponse,
    ExecutionGraphEdge,
    ExecutionGraphNode,
    ExecutionGraphResponse,
    IntelligenceModelRecord,
    IntelligenceOverviewResponse,
    OutcomePredictionResponse,
    ReflectionReportResponse,
    RiskLevel,
    SimilarTaskResponse,
    SimulationResponse,
    StrategyProfileResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "goal",
    "task",
    "plan",
    "need",
    "want",
    "build",
    "make",
    "create",
    "project",
    "user",
    "should",
    "would",
    "about",
    "into",
    "using",
    "without",
    "have",
    "will",
    "can",
    "could",
    "should",
}
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "product": ["launch", "saas", "product", "growth", "pricing", "market", "customer"],
    "engineering": ["api", "backend", "frontend", "service", "integration", "database", "deploy"],
    "operations": ["process", "workflow", "automation", "ops", "compliance", "report", "monitor"],
    "sales": ["sales", "pipeline", "revenue", "lead", "crm", "demo", "outreach"],
    "research": ["research", "analysis", "study", "investigation", "benchmark", "evaluate"],
    "content": ["content", "write", "blog", "article", "copy", "message", "brand"],
}


@dataclass(slots=True)
class _TaskSimilarity:
    task: Dict[str, Any]
    similarity: float


class IntelligenceService:
    def __init__(self, mongo, memory, reflector) -> None:
        self.mongo = mongo
        self.memory = memory
        self.reflector = reflector
        
        # Load ML Catalyst Model if available
        self.catalyst_model = None
        if ML_AVAILABLE:
            model_path = os.path.join("models", "pretrained", "catalyst_success_predictor.pkl")
            if os.path.exists(model_path):
                try:
                    self.catalyst_model = joblib.load(model_path)
                    logger.info("Loaded XGBoost Catalyst Model successfully.")
                except Exception as e:
                    logger.warning(f"Failed to load ML Catalyst Model: {e}")

    # ── Generic text helpers ───────────────────────────────────────────────

    def _tokens(self, text: str) -> List[str]:
        return [token for token in _TOKEN_RE.findall(text.lower()) if token not in _STOPWORDS]

    def _token_set(self, text: str) -> set[str]:
        return set(self._tokens(text))

    def _jaccard(self, left: str, right: str) -> float:
        left_tokens = self._token_set(left)
        right_tokens = self._token_set(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    def _clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, value))

    def _confidence_band(self, probability: float) -> str:
        if probability >= 0.8:
            return "high"
        if probability >= 0.6:
            return "medium"
        return "low"

    def _classify_domain(self, text: str) -> str:
        token_set = self._token_set(text)
        best_domain = "general"
        best_score = 0
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in token_set)
            if score > best_score:
                best_domain = domain
                best_score = score
        return best_domain

    def _summarise_context(self, context: Optional[Dict[str, Any]]) -> str:
        if not context:
            return ""
        return " ".join(f"{key}:{value}" for key, value in context.items())

    async def _all_tasks(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return await self.mongo.list_tasks(limit=1000, skip=0, user_id=user_id)

    def _task_text(self, task: Dict[str, Any]) -> str:
        return " ".join(
            str(part)
            for part in [
                task.get("goal", ""),
                task.get("research_insights", ""),
                task.get("execution_plan", ""),
                task.get("reasoning", ""),
            ]
        )

    def _build_mermaid(self, nodes: Sequence[ExecutionGraphNode], edges: Sequence[ExecutionGraphEdge]) -> str:
        lines = ["graph TD"]
        for node in nodes:
            label = node.label.replace('"', "'")
            lines.append(f'  {node.id}["{label}"]')
        for edge in edges:
            lines.append(f"  {edge.source} --> {edge.target}")
        return "\n".join(lines)

    def _risk_from_probability(self, probability: float) -> RiskLevel:
        if probability >= 0.75:
            return RiskLevel.LOW
        if probability >= 0.55:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    def _heuristic_probability(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        confidence: Optional[float],
        similarity_score: float,
        success_rate: float,
    ) -> Tuple[float, List[str], List[str]]:
        text = f"{goal} {self._summarise_context(context)}"
        domain = self._classify_domain(text)
        goal_len_factor = self._clamp(1.0 - max(0.0, (len(goal) - 220) / 1200.0))
        context_factor = 0.1 if context else -0.05
        confidence_factor = (confidence or 62.0) / 100.0
        probability = (
            confidence_factor * 0.46
            + similarity_score * 0.18
            + success_rate * 0.2
            + goal_len_factor * 0.1
            + context_factor
        )
        probability = self._clamp(probability, 0.05, 0.97)

        likely_failure_modes: List[str] = []
        recommended_safeguards: List[str] = []

        if probability < 0.45:
            likely_failure_modes.append("Scope is too broad for a single execution cycle.")
            recommended_safeguards.append("Break the goal into smaller milestones before execution.")
        if similarity_score < 0.25:
            likely_failure_modes.append("There is little historical precedent in the task archive.")
            recommended_safeguards.append("Require human review before committing resources.")
        if goal_len_factor < 0.75:
            likely_failure_modes.append("The goal is highly specific or time-boxed, leaving little recovery margin.")
            recommended_safeguards.append("Add explicit checkpoints and an approval gate.")
        if domain in {"engineering", "operations"}:
            recommended_safeguards.append("Validate dependencies and rollback steps before execution.")
        if domain == "sales":
            recommended_safeguards.append("Define a measurable funnel metric and daily review cadence.")

        return probability, likely_failure_modes, recommended_safeguards

    # ── Public overview/prediction API ─────────────────────────────────────

    async def overview(self, user_id: Optional[str] = None) -> IntelligenceOverviewResponse:
        tasks = await self._all_tasks(user_id=user_id)
        models = await self.mongo.list_intelligence_models()
        reports = await self.mongo.list_intelligence_reports(limit=100)
        if not tasks:
            return IntelligenceOverviewResponse(
                total_tasks=0,
                total_models=len(models),
                total_reports=len(reports),
                active_model=next((model["name"] for model in models if model.get("active")), None),
                average_confidence=0.0,
                recent_success_rate=0.0,
                drift_score=0.0,
                scheduled_reflection_status="idle",
                human_review_queue_size=0,
            )

        confidences = [float(task.get("confidence", 0.0)) for task in tasks]
        recent_slice = tasks[:20]
        resolved = [task for task in recent_slice if task.get("status") in {"COMPLETED", "FAILED"}]
        recent_success_rate = (
            sum(1 for task in resolved if task.get("status") == "COMPLETED") / len(resolved)
            if resolved
            else 0.5
        )
        drift = self._compute_drift(tasks)
        queue_size = sum(1 for task in tasks[:50] if float(task.get("confidence", 0)) < 55.0)
        return IntelligenceOverviewResponse(
            total_tasks=len(tasks),
            total_models=len(models),
            total_reports=len(reports),
            active_model=next((model["name"] for model in models if model.get("active")), None),
            average_confidence=round(mean(confidences), 2),
            recent_success_rate=round(recent_success_rate, 2),
            drift_score=round(drift, 3),
            scheduled_reflection_status="active" if settings.INTELLIGENCE_REFLECTION_INTERVAL_HOURS > 0 else "disabled",
            human_review_queue_size=queue_size,
        )

    async def build_execution_graph(self, task_id: str, user_id: Optional[str] = None) -> ExecutionGraphResponse:
        task = await self.memory.get_task(task_id, user_id=user_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        nodes: List[ExecutionGraphNode] = [ExecutionGraphNode(id="goal", label=task.get("goal", "Goal"), type="goal", status=task.get("status", "PENDING"))]
        edges: List[ExecutionGraphEdge] = []
        previous_id = "goal"

        raw_subtasks = task.get("subtasks", []) or []
        if not isinstance(raw_subtasks, list):
            raw_subtasks = []

        for index, subtask in enumerate(raw_subtasks, start=1):
            if not isinstance(subtask, dict):
                subtask = {"title": str(subtask), "dependencies": []}
            node_id = f"step_{index}"
            nodes.append(
                ExecutionGraphNode(
                    id=node_id,
                    label=str(subtask.get("title", f"Step {index}")),
                    type="subtask",
                    status=task.get("status", "PENDING"),
                )
            )
            edges.append(ExecutionGraphEdge(source=previous_id, target=node_id, label="sequence"))
            dependencies = subtask.get("dependencies", []) or []
            if not isinstance(dependencies, list):
                dependencies = [dependencies]

            for dependency in dependencies:
                dependency_text = str(dependency).strip()
                if not dependency_text:
                    continue
                tokens = self._tokens(dependency_text)
                dependency_id = f"dep_{index}_{tokens[0] if tokens else index}"
                nodes.append(
                    ExecutionGraphNode(
                        id=dependency_id,
                        label=dependency_text,
                        type="dependency",
                        status="linked",
                    )
                )
                edges.append(ExecutionGraphEdge(source=dependency_id, target=node_id, label="depends_on"))
            previous_id = node_id

        end_id = "result"
        nodes.append(ExecutionGraphNode(id=end_id, label="Outcome", type="outcome", status=task.get("status", "PENDING")))
        edges.append(ExecutionGraphEdge(source=previous_id, target=end_id, label="delivers"))
        mermaid = self._build_mermaid(nodes, edges)
        return ExecutionGraphResponse(task_id=task_id, goal=task.get("goal", ""), nodes=nodes, edges=edges, mermaid=mermaid)

    async def find_similar_tasks(
        self,
        task_id: Optional[str] = None,
        goal: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[SimilarTaskResponse]:
        tasks = await self._all_tasks(user_id=user_id)
        if task_id:
            source_task = await self.memory.get_task(task_id, user_id=user_id)
            if not source_task:
                raise ValueError(f"Task '{task_id}' not found.")
            goal = source_task.get("goal", "")

        if not goal:
            return []

        scored: List[_TaskSimilarity] = []
        for task in tasks:
            if task_id and task.get("task_id") == task_id:
                continue
            similarity = self._jaccard(goal, self._task_text(task))
            if similarity <= 0:
                continue
            scored.append(_TaskSimilarity(task=task, similarity=similarity))

        scored.sort(key=lambda item: item.similarity, reverse=True)
        responses: List[SimilarTaskResponse] = []
        for item in scored[:limit]:
            task = item.task
            responses.append(
                SimilarTaskResponse(
                    task_id=str(task.get("task_id", "")),
                    goal=str(task.get("goal", "")),
                    confidence=float(task.get("confidence", 0.0)),
                    risk_level=str(task.get("risk_level", "MEDIUM")),
                    similarity=round(item.similarity, 3),
                    status=str(task.get("status", "PENDING")),
                )
            )
        return responses

    async def build_strategy_profile(self, user_id: Optional[str] = None) -> StrategyProfileResponse:
        tasks = await self._all_tasks(user_id=user_id)
        if not tasks:
            return StrategyProfileResponse(
                user_id=user_id,
                profile_name="Default Explorer",
                strengths=["Clear goals", "Early validation"],
                watchouts=["No historical data yet"],
                preferred_approach="Start with a narrow milestone plan and gather evidence quickly.",
                success_rate=0.5,
                average_confidence=0.0,
                recent_domains=[],
            )

        completed = [task for task in tasks if task.get("status") == "COMPLETED"]
        success_rate = len(completed) / len([task for task in tasks if task.get("status") in {"COMPLETED", "FAILED", "IN_PROGRESS"}]) if any(task.get("status") in {"COMPLETED", "FAILED", "IN_PROGRESS"} for task in tasks) else 0.5
        average_confidence = mean(float(task.get("confidence", 0.0)) for task in tasks)
        domains = [self._classify_domain(self._task_text(task)) for task in tasks[:15]]
        domain_counts = Counter(domains)
        top_domains = [domain for domain, _ in domain_counts.most_common(3)]

        strengths: List[str] = []
        watchouts: List[str] = []
        preferred_approach = "Use short milestone loops, explicit approval gates, and outcome tracking."
        profile_name = "Balanced Operator"

        if average_confidence >= 72:
            profile_name = "High-Conviction Executor"
            strengths.append("Strong planning confidence")
            preferred_approach = "Move quickly on well-scoped work and keep a light review loop."
        elif average_confidence <= 55:
            profile_name = "Cautious Planner"
            strengths.append("Good at identifying risk early")
            watchouts.append("Tasks may need extra decomposition before execution")
        else:
            strengths.append("Balanced risk management")
            watchouts.append("Confidence and execution depth are fairly even")

        if success_rate >= 0.7:
            strengths.append("Consistent completion rate")
        elif success_rate <= 0.45:
            watchouts.append("Execution follow-through is below target")

        if top_domains:
            strengths.append(f"Frequent focus areas: {', '.join(top_domains)}")

        return StrategyProfileResponse(
            user_id=user_id,
            profile_name=profile_name,
            strengths=strengths[:4],
            watchouts=watchouts[:4],
            preferred_approach=preferred_approach,
            success_rate=round(success_rate, 2),
            average_confidence=round(average_confidence, 2),
            recent_domains=top_domains,
        )

    async def predict_outcome(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> OutcomePredictionResponse:
        similar = await self.find_similar_tasks(task_id=task_id, goal=goal, user_id=user_id, limit=8)
        success_tasks = await self._all_tasks(user_id=user_id)
        resolved = [task for task in success_tasks if task.get("status") in {"COMPLETED", "FAILED"}]
        success_rate = sum(1 for task in resolved if task.get("status") == "COMPLETED") / len(resolved) if resolved else 0.5
        similarity_score = mean([task.similarity for task in similar]) if similar else 0.0
        
        trust_comps = {"goal_clarity": 0.5, "information_quality": 0.5, "execution_feasibility": 0.5, "risk_manageability": 0.5, "resource_adequacy": 0.5, "external_uncertainty": 0.5}
        num_subtasks = 5
        if task_id:
            task_doc = await self.memory.get_task(task_id, user_id=user_id)
            if task_doc:
                if "trust_components" in task_doc and task_doc["trust_components"]:
                    trust_comps.update(task_doc["trust_components"])
                if "subtasks" in task_doc:
                    num_subtasks = len(task_doc["subtasks"])
                    
        probability = None
        if self.catalyst_model is not None:
            try:
                features = pd.DataFrame([{
                    "goal_length_words": len(goal.split()),
                    "num_subtasks": num_subtasks,
                    "clarity": float(trust_comps.get("goal_clarity", 0.5)),
                    "info_quality": float(trust_comps.get("information_quality", 0.5)),
                    "feasibility": float(trust_comps.get("execution_feasibility", 0.5)),
                    "manageability": float(trust_comps.get("risk_manageability", 0.5)),
                    "resource_adequacy": float(trust_comps.get("resource_adequacy", 0.5)),
                    "uncertainty": float(trust_comps.get("external_uncertainty", 0.5)),
                    "past_success_rate": float(success_rate),
                    "similarity_score": float(similarity_score)
                }])
                probability = float(self.catalyst_model.predict_proba(features)[0][1])
                failure_modes = ["Identified by ML Catalyst"] if probability < 0.5 else []
                safeguards = ["ML model flagged high risk"] if probability < 0.5 else []
                rationale = f"Predicted {probability:.1%} success using ML Catalyst model (XGBoost) based on {len(success_tasks)} historical data points."
                logger.info(f"ML Catalyst prediction: {probability:.3f}")
            except Exception as e:
                logger.error(f"ML Catalyst prediction failed: {e}. Falling back to heuristic.")
                probability = None

        if probability is None:
            probability, failure_modes, safeguards = self._heuristic_probability(goal, context, confidence, similarity_score, success_rate)
            rationale = (
                f"Predicted using {len(similar)} similar historical tasks, current confidence"
                f" {confidence if confidence is not None else 'n/a'}, and recent success rate {success_rate:.0%}."
            )
            
        risk_level = self._risk_from_probability(probability)
        human_review_required = probability < 0.65 or any("review" in safeguard.lower() for safeguard in safeguards)
        
        return OutcomePredictionResponse(
            task_id=task_id,
            predicted_success_probability=round(probability, 3),
            predicted_risk_level=risk_level,
            confidence_band=self._confidence_band(probability),
            human_review_required=human_review_required,
            likely_failure_modes=failure_modes,
            recommended_safeguards=safeguards,
            rationale=rationale,
        )

    async def simulate_execution(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        scenario: str = "baseline",
        user_id: Optional[str] = None,
    ) -> SimulationResponse:
        prediction = await self.predict_outcome(goal=goal, context=context, user_id=user_id)
        mitigation_steps = list(prediction.recommended_safeguards)
        if scenario.lower() != "baseline":
            mitigation_steps.append(f"Scenario-specific adjustment: test '{scenario}' assumptions early.")
        bottlenecks = prediction.likely_failure_modes or ["No major bottlenecks detected in this simulation."]
        return SimulationResponse(
            scenario=scenario,
            predicted_confidence=round(prediction.predicted_success_probability * 100, 1),
            predicted_risk_level=prediction.predicted_risk_level,
            success_probability=prediction.predicted_success_probability,
            bottlenecks=bottlenecks,
            mitigation_steps=mitigation_steps,
        )

    async def parse_workflow(self, workflow: str, title: str = "Workflow") -> Dict[str, Any]:
        lines = [line.strip() for line in workflow.splitlines() if line.strip()]
        nodes: Dict[str, str] = {}
        edges: List[Tuple[str, str]] = []

        def node_id(label: str) -> str:
            slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or f"node_{len(nodes) + 1}"
            if slug in nodes.values():
                slug = f"{slug}_{len(nodes) + 1}"
            return slug

        for line in lines:
            if "->" in line:
                parts = [part.strip() for part in line.split("->") if part.strip()]
                for left, right in zip(parts, parts[1:]):
                    left_id = next((nid for nid, label in nodes.items() if label == left), None) or node_id(left)
                    right_id = next((nid for nid, label in nodes.items() if label == right), None) or node_id(right)
                    nodes[left_id] = left
                    nodes[right_id] = right
                    edges.append((left_id, right_id))
            elif ":" in line:
                head, tail = [part.strip() for part in line.split(":", 1)]
                head_id = next((nid for nid, label in nodes.items() if label == head), None) or node_id(head)
                nodes[head_id] = head
                for child in [item.strip() for item in tail.split(",") if item.strip()]:
                    child_id = next((nid for nid, label in nodes.items() if label == child), None) or node_id(child)
                    nodes[child_id] = child
                    edges.append((head_id, child_id))
            else:
                current_id = node_id(line)
                nodes[current_id] = line

        mermaid_lines = [f"graph TD", f'  title["{title}"]']
        for node_id_value, label in nodes.items():
            mermaid_lines.append(f'  {node_id_value}["{label.replace("\"", "\'")}"]')
        for source, target in edges:
            mermaid_lines.append(f"  {source} --> {target}")
        return {
            "title": title,
            "nodes": [{"id": node_id_value, "label": label} for node_id_value, label in nodes.items()],
            "edges": [{"source": source, "target": target} for source, target in edges],
            "mermaid": "\n".join(mermaid_lines),
        }

    async def register_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = IntelligenceModelRecord(**payload)
        if record.active:
            await self.mongo._intelligence_models().update_many({}, {"$set": {"active": False}})
        await self.mongo.upsert_intelligence_model(record.model_dump())
        return record.model_dump()

    async def list_models(self) -> List[Dict[str, Any]]:
        return await self.mongo.list_intelligence_models()

    async def rollback_model(self, model_id: str) -> Dict[str, Any]:
        models = await self.list_models()
        target = next((model for model in models if model.get("model_id") == model_id), None)
        if not target:
            raise ValueError(f"Model '{model_id}' not found.")
        for model in models:
            await self.mongo.upsert_intelligence_model({**model, "active": model.get("model_id") == model_id, "updated_at": datetime.utcnow()})
        return {"model_id": model_id, "status": "rolled_back", "active": True}

    async def compute_drift(self, user_id: Optional[str] = None) -> DriftReportResponse:
        tasks = await self._all_tasks(user_id=user_id)
        if not tasks:
            return DriftReportResponse(
                drift_score=0.0,
                baseline_confidence=0.0,
                recent_confidence=0.0,
                baseline_success_rate=0.0,
                recent_success_rate=0.0,
                retraining_recommended=False,
                notes=["No task history available."],
            )

        recent = tasks[:10]
        baseline = tasks[10:50] if len(tasks) > 10 else tasks
        recent_conf = mean(float(task.get("confidence", 0.0)) for task in recent)
        baseline_conf = mean(float(task.get("confidence", 0.0)) for task in baseline)

        def success_rate(rows: List[Dict[str, Any]]) -> float:
            resolved = [task for task in rows if task.get("status") in {"COMPLETED", "FAILED"}]
            if not resolved:
                return 0.5
            return sum(1 for task in resolved if task.get("status") == "COMPLETED") / len(resolved)

        recent_success = success_rate(recent)
        baseline_success = success_rate(baseline)
        drift_score = self._clamp(abs(recent_conf - baseline_conf) / 100.0 + abs(recent_success - baseline_success) / 2.0, 0.0, 1.0)
        notes = []
        if abs(recent_conf - baseline_conf) > 8:
            notes.append("Recent confidence has shifted materially from baseline.")
        if abs(recent_success - baseline_success) > 0.15:
            notes.append("Recent outcome success rate differs from historical baseline.")
        if drift_score >= 0.25:
            notes.append("Retraining or calibration review is recommended.")
        return DriftReportResponse(
            drift_score=round(drift_score, 3),
            baseline_confidence=round(baseline_conf, 2),
            recent_confidence=round(recent_conf, 2),
            baseline_success_rate=round(baseline_success, 2),
            recent_success_rate=round(recent_success, 2),
            retraining_recommended=drift_score >= 0.25,
            notes=notes or ["No significant drift detected."],
        )

    async def refresh_reflection_report(self, sample_size: int = 20) -> ReflectionReportResponse:
        report = await self.reflector.run_global_reflection(sample_size=sample_size)
        response = ReflectionReportResponse(
            generated_at=datetime.utcnow(),
            lessons=list(report.get("lessons", [])),
            pattern_summary=str(report.get("pattern_summary", "")),
            confidence_calibration_note=str(report.get("confidence_calibration_note", "")),
            suggested_weight_adjustments=dict(report.get("suggested_weight_adjustments", {})),
            updated_confidence_bias=float(report.get("updated_confidence_bias", 0.0)),
        )
        await self.mongo.save_intelligence_report({**response.model_dump(), "report_type": "reflection"})
        return response

    async def upsert_default_model(self) -> Dict[str, Any]:
        models = await self.list_models()
        if models:
            return models[0]
        default = IntelligenceModelRecord(
            name="Catalyst Heuristic v1",
            version="1.0.0",
            description="Baseline heuristic predictor for route, risk, and confidence calibration.",
            status="active",
            metrics={"source": "heuristic", "precision": 0.67, "recall": 0.64},
            active=True,
        )
        await self.mongo.upsert_intelligence_model(default.model_dump())
        return default.model_dump()

    async def save_manual_override(self, task_id: str, decision: str, notes: Optional[str] = None) -> Dict[str, Any]:
        await self.mongo.save_intelligence_report(
            {
                "report_type": "manual_override",
                "task_id": task_id,
                "decision": decision,
                "notes": notes,
                "created_at": datetime.utcnow(),
            }
        )
        return {"task_id": task_id, "decision": decision, "notes": notes}

    async def ensure_scheduled_report(self) -> Dict[str, Any]:
        response = await self.refresh_reflection_report(sample_size=20)
        return {"generated_at": response.generated_at.isoformat(), "lessons": len(response.lessons)}

    # ── Internal analytics ──────────────────────────────────────────────────

    def _compute_drift(self, tasks: Sequence[Dict[str, Any]]) -> float:
        if len(tasks) < 2:
            return 0.0
        recent = tasks[:10]
        baseline = tasks[10:50] if len(tasks) > 10 else tasks
        recent_conf = mean(float(task.get("confidence", 0.0)) for task in recent)
        baseline_conf = mean(float(task.get("confidence", 0.0)) for task in baseline)
        recent_success = sum(1 for task in recent if task.get("status") == "COMPLETED") / len(recent)
        baseline_resolved = [task for task in baseline if task.get("status") in {"COMPLETED", "FAILED"}]
        baseline_success = (
            sum(1 for task in baseline_resolved if task.get("status") == "COMPLETED") / len(baseline_resolved)
            if baseline_resolved
            else 0.5
        )
        return self._clamp(abs(recent_conf - baseline_conf) / 100.0 + abs(recent_success - baseline_success) / 2.0, 0.0, 1.0)
