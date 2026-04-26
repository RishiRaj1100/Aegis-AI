"""
AegisAI - Intelligence Service
Heuristic execution intelligence layer for graphing, similarity search,
prediction, simulation, registry management, and scheduled reflection reports.
"""

from __future__ import annotations

import logging
import os
import re
import warnings
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
from services.explainability import ExplainabilityService

# Suppress scikit-learn version warnings for pretrained models
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.base")

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
        self.explainability = ExplainabilityService()
        
        # Load ML Catalyst Models if available
        self.catalyst_model = None
        self.delay_model = None
        if ML_AVAILABLE:
            success_path = os.path.join("models", "pretrained", "catalyst_success_predictor.pkl")
            delay_path = os.path.join("models", "pretrained", "behavior_model.pkl")
            
            if os.path.exists(success_path):
                try:
                    self.catalyst_model = joblib.load(success_path)
                    logger.info("Loaded XGBoost Catalyst Success Model.")
                except Exception as e:
                    logger.warning(f"Failed to load Success Model: {e}")
                    
            if os.path.exists(delay_path):
                try:
                    self.delay_model = joblib.load(delay_path)
                    logger.info("Loaded Logistic Delay Model.")
                except Exception as e:
                    logger.warning(f"Failed to load Delay Model: {e}")

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
        lines = ["flowchart TD"]
        for node in nodes:
            # Robustly sanitize labels for Mermaid: replace double quotes with single, remove newlines
            label = str(node.label).replace('"', "'").replace("\n", " ").replace("\r", " ").strip()
            # Ensure node IDs are valid (alphanumeric + underscores)
            safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(node.id))
            lines.append(f'  {safe_id}["{label}"]')
        for edge in edges:
            src = re.sub(r"[^a-zA-Z0-9_]", "_", str(edge.source))
            tgt = re.sub(r"[^a-zA-Z0-9_]", "_", str(edge.target))
            lines.append(f"  {src} --> {tgt}")
        return "\n".join(lines)

    def _extract_plan_phases(self, execution_plan: str) -> List[str]:
        phases: List[str] = []
        for raw_line in execution_plan.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            stripped = line.lstrip("#").strip()
            if stripped.lower().startswith("phase"):
                phases.append(stripped)
        return phases

    def _context_support_score(self, context: Optional[Dict[str, Any]]) -> float:
        if not context:
            return 0.45

        signals = 0.45
        lowered_keys = {str(key).lower(): value for key, value in context.items()}
        if lowered_keys.get("budget"):
            signals += 0.08
        if lowered_keys.get("team_size"):
            try:
                team_size = float(lowered_keys.get("team_size", 0))
                if team_size >= 3:
                    signals += 0.1
                elif team_size == 1:
                    signals -= 0.03
            except Exception:
                signals += 0.02
        if lowered_keys.get("deadline") or lowered_keys.get("days_until_deadline"):
            signals += 0.06
        if lowered_keys.get("blockers"):
            blockers = lowered_keys.get("blockers")
            blocker_count = len(blockers) if isinstance(blockers, list) else 1
            signals -= min(blocker_count * 0.04, 0.15)
        if lowered_keys.get("resources"):
            signals += 0.05
        return self._clamp(signals, 0.05, 0.95)

    def _case_signal(self, similar: Sequence[_TaskSimilarity]) -> float:
        if not similar:
            return 0.5
        total = sum(item.similarity for item in similar)
        resolved = [item for item in similar if str(getattr(item, "status", "")).upper() in {"COMPLETED", "FAILED"}]
        if resolved:
            completed = sum(item.similarity for item in resolved if str(getattr(item, "status", "")).upper() == "COMPLETED")
            resolved_total = sum(item.similarity for item in resolved)
            resolved_rate = completed / resolved_total if resolved_total > 0 else 0.5
        else:
            resolved_rate = 0.5
        avg_similarity = total / len(similar)
        return self._clamp((resolved_rate * 0.6) + (avg_similarity * 0.4), 0.05, 0.95)

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

        raw_subtasks = task.get("subtasks", []) or []
        if not isinstance(raw_subtasks, list):
            raw_subtasks = []

        phases = self._extract_plan_phases(str(task.get("execution_plan", "")))
        phase_ids: List[str] = []
        if phases:
            nodes.append(ExecutionGraphNode(id="phase_anchor", label="Execution Plan", type="phase", status=task.get("status", "PENDING")))
            edges.append(ExecutionGraphEdge(source="goal", target="phase_anchor", label="plan"))
            for index, phase_label in enumerate(phases, start=1):
                phase_id = f"phase_{index}"
                phase_ids.append(phase_id)
                nodes.append(
                    ExecutionGraphNode(
                        id=phase_id,
                        label=phase_label,
                        type="phase",
                        status=task.get("status", "PENDING"),
                    )
                )
                parent_id = "phase_anchor" if index == 1 else phase_ids[index - 2]
                edges.append(ExecutionGraphEdge(source=parent_id, target=phase_id, label="sequence"))

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
            if phase_ids:
                phase_index = min((index - 1) * len(phase_ids) // max(len(raw_subtasks), 1), len(phase_ids) - 1)
                edges.append(ExecutionGraphEdge(source=phase_ids[phase_index], target=node_id, label="executes"))
            else:
                previous_id = "goal" if index == 1 else f"step_{index - 1}"
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

        end_id = "result"
        outcome_label = f"Outcome: {task.get('status', 'PENDING')}"
        outcome_notes = str(task.get("outcome_notes", "")).strip()
        if outcome_notes:
            outcome_label = f"{outcome_label} | {outcome_notes[:60]}"
        nodes.append(ExecutionGraphNode(id=end_id, label=outcome_label, type="outcome", status=task.get("status", "PENDING")))

        if phase_ids:
            edges.append(ExecutionGraphEdge(source=phase_ids[-1], target=end_id, label="delivers"))
        elif raw_subtasks:
            edges.append(ExecutionGraphEdge(source=f"step_{len(raw_subtasks)}", target=end_id, label="delivers"))
        else:
            edges.append(ExecutionGraphEdge(source="goal", target=end_id, label="delivers"))

        reflections = await self.memory.get_reflections(task_id)
        if reflections:
            latest = reflections[0]
            reflection_label = str(latest.get("lesson", "Reflection note"))[:90]
            nodes.append(ExecutionGraphNode(id="reflection", label=reflection_label, type="memory", status="recorded"))
            edges.append(ExecutionGraphEdge(source=end_id, target="reflection", label="learns_from"))

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
            updated_at = task.get("updated_at") or task.get("created_at")
            if hasattr(updated_at, "timestamp"):
                age_days = max((datetime.utcnow() - updated_at).days, 0)
                similarity += self._clamp(1.0 - min(age_days / 30.0, 1.0), 0.0, 1.0) * 0.08
            status = str(task.get("status", "")).upper()
            if status == "COMPLETED":
                similarity += 0.03
            elif status == "FAILED":
                similarity += 0.01
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
        similar_cases = self.explainability.retrieve_similar_cases(
            query_text=goal,
            tasks=success_tasks,
            top_k=5,
            exclude_task_id=task_id,
        )
        resolved = [task for task in success_tasks if task.get("status") in {"COMPLETED", "FAILED"}]
        success_rate = sum(1 for task in resolved if task.get("status") == "COMPLETED") / len(resolved) if resolved else 0.5
        similarity_score = mean([task.similarity for task in similar]) if similar else 0.0
        case_signal = self._case_signal(similar)
        context_signal = self._context_support_score(context)

        trust_comps = {"goal_clarity": 0.5, "information_quality": 0.5, "execution_feasibility": 0.5, "risk_manageability": 0.5, "resource_adequacy": 0.5, "external_uncertainty": 0.5}
        num_subtasks = 5
        task_status = "PENDING"
        reflections: List[Dict[str, Any]] = []
        if task_id:
            task_doc = await self.memory.get_task(task_id, user_id=user_id)
            if task_doc:
                if task_doc.get("trust_components"):
                    trust_comps.update(task_doc["trust_components"])
                if task_doc.get("subtasks"):
                    num_subtasks = len(task_doc["subtasks"])
                task_status = str(task_doc.get("status", "PENDING"))
                reflections = await self.memory.get_reflections(task_id)

        trust_signal = mean(
            [
                float(trust_comps.get("goal_clarity", 0.5)),
                float(trust_comps.get("information_quality", 0.5)),
                float(trust_comps.get("execution_feasibility", 0.5)),
                float(trust_comps.get("risk_manageability", 0.5)),
                float(trust_comps.get("resource_adequacy", 0.5)),
                1.0 - float(trust_comps.get("external_uncertainty", 0.5)),
            ]
        )
        reflection_signal = self._clamp(0.45 + min(len(reflections), 5) * 0.08, 0.05, 0.95) if reflections else 0.45

        probability = None
        shap_values: Dict[str, float] = {}
        positive_factors: List[str] = []
        negative_factors: List[str] = []
        failure_modes: List[str] = []
        safeguards: List[str] = []

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
                    "similarity_score": float(similarity_score),
                    "case_signal": float(case_signal),
                    "context_signal": float(context_signal),
                    "trust_signal": float(trust_signal),
                    "reflection_signal": float(reflection_signal),
                }])
                model_probability = float(self.catalyst_model.predict_proba(features)[0][1])
                evidence_prior = self._clamp(
                    0.34 * success_rate
                    + 0.28 * case_signal
                    + 0.16 * trust_signal
                    + 0.12 * context_signal
                    + 0.10 * reflection_signal,
                    0.05,
                    0.95,
                )
                probability = self._clamp(0.65 * model_probability + 0.35 * evidence_prior, 0.05, 0.97)
                shap_values, positive_factors, negative_factors = self.explainability.explain_prediction(
                    model=self.catalyst_model,
                    features=features,
                    top_k=3,
                )
                logger.info("ML Catalyst prediction: %.3f", probability)
            except Exception as e:
                logger.error("ML Catalyst prediction failed: %s. Falling back to evidence blend.", e)
                probability = None

        if probability is None:
            probability = self._clamp(
                0.38 * success_rate
                + 0.26 * case_signal
                + 0.18 * trust_signal
                + 0.10 * context_signal
                + 0.08 * reflection_signal,
                0.05,
                0.97,
            )
            if success_rate < 0.5:
                failure_modes.append("Historical resolved tasks suggest below-average completion odds.")
                safeguards.append("Reduce scope before execution.")
            else:
                positive_factors.append("Historical task outcomes are at least neutral.")
            if case_signal < 0.5:
                failure_modes.append("Nearest similar cases do not strongly support success.")
                safeguards.append("Ask for more context or evidence.")
            else:
                positive_factors.append("The nearest historical cases provide supporting evidence.")
            if trust_signal < 0.5:
                failure_modes.append("Goal clarity or resource adequacy is weak.")
                safeguards.append("Clarify ownership and resource commitments.")
            else:
                positive_factors.append("The trust components indicate the goal is reasonably formed.")
            if context_signal < 0.45:
                failure_modes.append("Provided context suggests pressure or missing inputs.")
                safeguards.append("Add checkpoints and block if key inputs are absent.")
            if reflections:
                positive_factors.append("Past feedback and reflections provide calibration signals.")
            if not positive_factors:
                positive_factors.append("The goal is analyzable, but evidence is thin.")
            rationale = (
                f"Predicted using {len(resolved)} resolved historical tasks, {len(similar)} similarity matches, and {len(reflections)} prior reflections. "
                f"The evidence prior is driven by task history instead of a static default probability."
            )
        else:
            failure_modes = []
            safeguards = []
            if success_rate < 0.5:
                failure_modes.append("Historical resolved tasks are trending toward failure.")
                safeguards.append("Review the closest completed/failed cases before acting.")
            if case_signal < 0.5:
                failure_modes.append("The nearest historical cases are not strongly supportive.")
                safeguards.append("Collect more evidence from comparable tasks.")
            if trust_signal < 0.5:
                failure_modes.append("Task definitions or resource signals are weak.")
                safeguards.append("Tighten scope and confirm resource availability.")
            if context_signal < 0.45:
                failure_modes.append("Context suggests pressure or missing information.")
                safeguards.append("Add explicit assumptions and approval checkpoints.")
            rationale = (
                f"Predicted {probability:.1%} success from the catalyst model blended with historical task outcomes, similar-case signals, and reflection history. "
                f"The model was calibrated against {len(resolved)} resolved tasks and {len(similar)} nearest matches."
            )

        risk_level = self._risk_from_probability(probability)
        human_review_required = probability < 0.65 or any("review" in safeguard.lower() for safeguard in safeguards) or task_status in {"FAILED", "BLOCKED"}
        
        return OutcomePredictionResponse(
            task_id=task_id,
            predicted_success_probability=round(probability, 3),
            success_probability=round(probability, 3),
            predicted_risk_level=risk_level,
            confidence_band=self._confidence_band(probability),
            human_review_required=human_review_required,
            likely_failure_modes=failure_modes,
            recommended_safeguards=safeguards,
            rationale=rationale,
            explanation={
                "positive_factors": positive_factors[:3],
                "negative_factors": negative_factors[:3],
            },
            shap_values={k: round(v, 6) for k, v in shap_values.items()},
            similar_cases=similar_cases,
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

        mermaid_lines = ["flowchart TD"]
        # Add a title node if title is provided
        if title:
            safe_title = title.replace('"', "'").replace("\n", " ")
            mermaid_lines.append(f'  title["{safe_title}"]')
            
        for node_id_value, label in nodes.items():
            # Robustly sanitize labels: replace double quotes with single, remove newlines
            safe_label = str(label).replace('"', "'").replace("\n", " ").replace("\r", " ").strip()
            mermaid_lines.append(f'  {node_id_value}["{safe_label}"]')
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

    async def build_memory_graph(self, user_id: Optional[str] = None) -> MemoryGraphResponse:
        """
        Build a global experience graph for a user, connecting similar missions
        to show how AegisAI transfers knowledge between them.
        """
        tasks = await self._all_tasks(user_id=user_id)
        if not tasks:
            return ExecutionGraphResponse(
                task_id="global",
                goal="Memory Graph",
                nodes=[],
                edges=[],
                mermaid="graph TD\n  Empty[No missions recorded]"
            )

        nodes: List[ExecutionGraphNode] = []
        edges: List[ExecutionGraphEdge] = []
        
        # Limit to recent 50 tasks for performance in the graph
        display_tasks = tasks[:50]
        
        for task in display_tasks:
            nodes.append(ExecutionGraphNode(
                id=str(task.get("task_id", "")),
                label=str(task.get("goal", ""))[:40] + "...",
                type="task",
                status=str(task.get("status", "completed")).lower()
            ))

        # Calculate similarity edges between missions
        for i, t1 in enumerate(display_tasks):
            for j, t2 in enumerate(display_tasks):
                if i >= j: continue
                
                similarity = self._jaccard(
                    t1.get("goal", ""), 
                    t2.get("goal", "")
                )
                
                # If similarity is above threshold, create an edge
                if similarity >= 0.25:
                    edges.append(ExecutionGraphEdge(
                        source=str(t1.get("task_id", "")),
                        target=str(t2.get("task_id", "")),
                        label="similar_to"
                    ))

        # Build Mermaid string
        mermaid_lines = ["graph LR"]
        for node in nodes:
            label = node.label.replace('"', "'")
            mermaid_lines.append(f'  {node.id}["{label}"]')
        for edge in edges:
            mermaid_lines.append(f"  {edge.source} -- {edge.label} --> {edge.target}")
            
        return ExecutionGraphResponse(
            task_id="global",
            goal="Memory Graph",
            nodes=nodes,
            edges=edges,
            mermaid="\n".join(mermaid_lines)
        )

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

