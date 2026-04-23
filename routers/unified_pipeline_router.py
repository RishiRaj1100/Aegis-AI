"""
UNIFIED API ROUTER — Complete AegisAI Autonomous Decision Intelligence API
Exposes all pipeline stages: verification → reasoning → debate → prioritization
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import logging

from core.aegis_pipeline import get_aegis_pipeline, PipelineResult
from agents.truth_agent import get_trust_agent, RiskLevel
from engines.nyaya_reasoning import get_nyaya_reasoning_engine
from agents.multi_agent_debater import get_multi_agent_debater
from engines.prioritization_engine import get_prioritization_engine
from agents.execution_agent import SafeExecutionAgent
from services.mongodb_service import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/aegis", tags=["AegisAI Autonomous Intelligence"])


# ──────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────────────────────────

class TaskInput(BaseModel):
    """Input task for analysis."""
    task_id: str
    description: str = Field(..., min_length=10, max_length=5000)
    business_impact: float = Field(default=1.0, ge=0, le=1)
    estimated_effort_hours: float = Field(default=10, ge=0.5, le=500)
    deadline: Optional[str] = None
    requires_team: bool = False
    blockers: List[str] = []


class ExecuteCommandInput(BaseModel):
    """Input for safe command execution."""
    command: str = Field(..., max_length=1000)
    timeout_seconds: int = Field(default=300, ge=10, le=3600)


class FeedbackInput(BaseModel):
    """User feedback on task outcome."""
    task_id: str
    predicted_success: bool
    actual_success: bool
    actual_effort_hours: float
    notes: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Core Pipeline Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=Dict)
async def analyze_task(
    task: TaskInput,
    user_id: Optional[str] = Query(None)
):
    """
    Complete autonomous analysis pipeline.
    
    Runs:
    1. Trust verification (risk assessment)
    2. NYAYA reasoning (explainable logic)
    3. Multi-agent debate (consensus building)
    4. Prioritization (task ranking)
    
    Returns full decision with confidence scores and recommendations.
    """
    try:
        logger.info(f"[API] /analyze → task_id={task.task_id}")
        
        pipeline = get_aegis_pipeline()
        
        task_features = {
            "business_impact": task.business_impact,
            "estimated_effort_hours": task.estimated_effort_hours,
            "deadline": task.deadline,
            "requires_team": task.requires_team,
            "blockers": task.blockers,
        }
        
        result = pipeline.execute(
            task_id=task.task_id,
            task_description=task.description,
            task_features=task_features,
            user_id=user_id
        )
        
        return {
            "success": True,
            "task_id": result.task_id,
            "decision": {
                "should_execute": result.should_execute,
                "recommendation": result.final_recommendation,
                "priority_score": result.priority_score,
                "success_probability": result.debate_result.central_forecast,
            },
            "verification": {
                "risk_level": result.verification.risk_level.value,
                "risk_score": result.verification.risk_score,
                "confidence_score": result.verification.confidence_score,
                "blocking_reason": result.verification.blocking_reason,
            },
            "reasoning": {
                "success_probability": result.reasoning_trace.final_prediction,
                "key_factors": result.reasoning_trace.key_factors,
                "recommendations": result.reasoning_trace.recommendations,
            },
            "debate": {
                "optimistic_forecast": result.debate_result.optimistic_forecast.success_probability,
                "risk_forecast": result.debate_result.risk_forecast.success_probability,
                "execution_forecast": result.debate_result.execution_forecast.success_probability,
                "consensus_level": result.debate_result.consensus_level.value,
                "conflicts": result.debate_result.conflicts,
            },
            "mitigations": result.risk_mitigations,
            "latency_ms": result.total_latency_ms,
        }
    except Exception as e:
        logger.error(f"[API] /analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Verification Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/verify")
async def verify_claim(
    claim: str = Body(..., embed=True),
    context: Optional[Dict] = Body(None),
    user_id: Optional[str] = Query(None)
):
    """
    Verify a claim and assess risk.
    
    Returns:
    - Risk score and level
    - Confidence score
    - Supporting evidence from similar cases
    - Blocking reason (if applicable)
    """
    try:
        logger.info(f"[API] /verify → claim={claim[:50]}")
        
        trust_agent = get_trust_agent()
        result = trust_agent.verify_claim(claim=claim, context=context, user_id=user_id)
        
        return {
            "verified": result.is_verified,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level.value,
            "confidence_score": result.confidence_score,
            "reasoning": result.reasoning,
            "mitigations": result.mitigations,
            "blocking_reason": result.blocking_reason,
            "evidence_count": len(result.evidence),
        }
    except Exception as e:
        logger.error(f"[API] /verify error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Reasoning Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/reason")
async def explain_reasoning(
    task: TaskInput,
    user_id: Optional[str] = Query(None)
):
    """
    Get detailed NYAYA-style reasoning for a task.
    
    Returns full reasoning chain with four Pramanas:
    - Pratyaksha (direct observation)
    - Upamana (analogy from similar cases)
    - Anumana (logical inference)
    - Sabda (historical best practices)
    """
    try:
        logger.info(f"[API] /reason → task_id={task.task_id}")
        
        engine = get_nyaya_reasoning_engine()
        task_features = {
            "business_impact": task.business_impact,
            "estimated_effort_hours": task.estimated_effort_hours,
            "requires_team": task.requires_team,
        }
        
        trace = engine.reason_about_task(
            task_id=task.task_id,
            task_description=task.description,
            task_features=task_features,
            user_id=user_id
        )
        
        return {
            "task_id": trace.task_id,
            "reasoning_chain": [
                {
                    "step": s.step_number,
                    "pramana": s.pramana.value,
                    "premise": s.premise,
                    "conclusion": s.conclusion,
                    "confidence": s.confidence,
                }
                for s in trace.reasoning_chain
            ],
            "key_factors": trace.key_factors,
            "final_prediction": trace.final_prediction,
            "confidence_score": trace.confidence_score,
            "recommendations": trace.recommendations,
        }
    except Exception as e:
        logger.error(f"[API] /reason error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Debate Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/debate")
async def multi_agent_debate(
    task: TaskInput,
    user_id: Optional[str] = Query(None)
):
    """
    Run multi-agent debate on a task.
    
    Three agents debate:
    - Optimistic Agent (bullish forecast)
    - Risk Agent (conservative forecast)
    - Execution Agent (feasibility check)
    
    Returns consensus and conflicts.
    """
    try:
        logger.info(f"[API] /debate → task_id={task.task_id}")
        
        debater = get_multi_agent_debater()
        task_features = {
            "business_impact": task.business_impact,
            "estimated_effort_hours": task.estimated_effort_hours,
            "requires_team": task.requires_team,
            "blockers": task.blockers,
        }
        
        # Placeholder: would retrieve similar cases
        similar_cases = []
        
        result = debater.debate(
            task_id=task.task_id,
            task_description=task.description,
            task_features=task_features,
            similar_cases=similar_cases,
            user_id=user_id
        )
        
        return {
            "central_forecast": result.central_forecast,
            "optimistic_forecast": result.optimistic_forecast.success_probability,
            "risk_forecast": result.risk_forecast.success_probability,
            "execution_forecast": result.execution_forecast.success_probability,
            "consensus_level": result.consensus_level.value,
            "consensus_confidence": result.consensus_confidence,
            "conflicts": result.conflicts,
            "final_recommendation": result.final_recommendation,
        }
    except Exception as e:
        logger.error(f"[API] /debate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Prioritization Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/prioritize")
async def rank_tasks(
    tasks: List[TaskInput],
    forecasts: Dict[str, float] = Body(...),  # task_id → success_probability
):
    """
    Rank multiple tasks by priority.
    
    Formula: Priority = (Impact × Success_Prob × Urgency) / (Effort × Blockers)
    
    Returns ranked list with priorities and breakdown.
    """
    try:
        logger.info(f"[API] /prioritize → {len(tasks)} tasks")
        
        engine = get_prioritization_engine()
        
        task_docs = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "business_impact": t.business_impact,
                "estimated_effort_hours": t.estimated_effort_hours,
                "deadline": t.deadline,
                "blockers": t.blockers,
            }
            for t in tasks
        ]
        
        ranked = engine.rank_tasks(task_docs, forecasts)
        
        return {
            "ranked_tasks": [
                {
                    "task_id": r.task_id,
                    "rank": r.rank,
                    "priority_score": r.priority_score,
                    "success_probability": r.success_probability,
                    "justification": r.justification,
                    "should_break": engine.should_break_into_subtasks(r),
                }
                for r in ranked
            ]
        }
    except Exception as e:
        logger.error(f"[API] /prioritize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Behavior Intelligence Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/behavior")
async def analyze_task_behavior(
    task: TaskInput,
    user_id: Optional[str] = Query(None)
):
    """
    Analyze task behavior for delays and abandonment risk.
    
    Returns:
    - Delay probability and estimated delay days
    - Abandonment risk level and probability
    - Risk factors and success indicators
    - Mitigation suggestions
    - Reordering recommendation
    """
    try:
        logger.info(f"[API] /behavior → task_id={task.task_id}")
        
        from engines.behavior_intelligence import get_behavior_intelligence_engine
        behavior_engine = get_behavior_intelligence_engine()
        
        task_features = {
            "complexity": task.business_impact,  # Use impact as complexity proxy
            "effort_estimate_hours": task.estimated_effort_hours,
            "team_size": 1 if not task.requires_team else 3,
        }
        
        analysis = behavior_engine.analyze_task_behavior(
            task_id=task.task_id,
            task_features=task_features,
            user_id=user_id
        )
        
        return {
            "task_id": analysis.task_id,
            "delay_analysis": {
                "delay_probability": analysis.delay_probability,
                "estimated_delay_days": analysis.delay_days,
                "delay_pattern": analysis.delay_pattern.value,
            },
            "abandonment_analysis": {
                "abandonment_probability": analysis.abandonment_probability,
                "abandonment_risk": analysis.abandonment_risk.value,
            },
            "risk_factors": analysis.risk_factors,
            "success_indicators": analysis.success_indicators,
            "mitigations": analysis.mitigation_suggestions,
            "reorder_recommendation": analysis.reorder_recommendation,
            "confidence_score": analysis.confidence_score,
        }
    except Exception as e:
        logger.error(f"[API] /behavior error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Execution Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/execute")
async def safe_execute(
    execution: ExecuteCommandInput,
    user_id: Optional[str] = Query(None)
):
    """
    Execute a command safely with sandboxing.
    
    Features:
    - Whitelist validation
    - Timeout enforcement
    - Resource isolation
    - Full audit logging
    """
    try:
        logger.info(f"[API] /execute → command={execution.command[:50]}")
        
        executor = SafeExecutionAgent()
        result = executor.execute(
            command=execution.command,
            timeout=execution.timeout_seconds,
            user_id=user_id
        )
        
        return {
            "status": result.status.value,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration_seconds": result.duration_seconds,
        }
    except Exception as e:
        logger.error(f"[API] /execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Feedback Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/feedback")
async def record_feedback(
    feedback: FeedbackInput,
    user_id: Optional[str] = Query(None)
):
    """
    Record user feedback on task outcome.
    
    Used for continuous learning and model retraining.
    """
    try:
        logger.info(f"[API] /feedback → task_id={feedback.task_id}")
        
        pipeline = get_aegis_pipeline()
        result = pipeline.record_feedback(
            task_id=feedback.task_id,
            predicted_success=feedback.predicted_success,
            actual_success=feedback.actual_success,
            actual_effort_hours=feedback.actual_effort_hours,
            notes=feedback.notes,
            user_id=user_id
        )
        
        return {
            "recorded": result["recorded"],
            "prediction_accuracy": result["prediction_accuracy"],
            "feedback_id": result["feedback_id"],
        }
    except Exception as e:
        logger.error(f"[API] /feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Metrics Recording Endpoint
# ──────────────────────────────────────────────────────────────────────────────

class PredictionMetricInput(BaseModel):
    """Input for recording prediction metrics."""
    task_id: str
    predicted_success: bool
    predicted_probability: float = Field(ge=0, le=1)
    actual_success: bool


@router.post("/metrics/prediction")
async def record_prediction_metric(
    metric: PredictionMetricInput,
    user_id: Optional[str] = Query(None)
):
    """
    Record prediction vs actual outcome for metrics tracking.
    
    Used for model calibration, accuracy monitoring, and drift detection.
    """
    try:
        logger.info(f"[API] /metrics/prediction → task_id={metric.task_id}")
        
        from services.metrics_service import get_metrics_collector
        collector = get_metrics_collector()
        
        result = collector.record_prediction(
            task_id=metric.task_id,
            predicted_success=metric.predicted_success,
            predicted_probability=metric.predicted_probability,
            actual_success=metric.actual_success,
            user_id=user_id
        )
        
        return {
            "recorded": result["recorded"],
            "task_id": result["task_id"],
        }
    except Exception as e:
        logger.error(f"[API] /metrics/prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Metrics Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_system_metrics():
    """Get comprehensive system-wide performance metrics."""
    try:
        logger.info("[API] /metrics → collecting comprehensive metrics")
        
        from services.metrics_service import get_metrics_collector
        collector = get_metrics_collector()
        
        dashboard_summary = collector.get_dashboard_summary()
        
        return {
            "success": True,
            "data": dashboard_summary
        }
    except Exception as e:
        logger.error(f"[API] /metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# A/B Testing Endpoints
# ──────────────────────────────────────────────────────────────────────────────

class ExperimentMetricInput(BaseModel):
    """Input for tracking experiment metrics."""
    experiment_id: str
    user_id: str
    group: str  # "A" or "B"
    metric_name: str
    metric_value: float


@router.post("/experiments/assign")
async def assign_experiment_group(
    user_id: str = Query(None),
    experiment_id: str = Query(default="prioritization_v1")
):
    """
    Assign user to A/B test group.
    
    Returns:
    - group: "A" (control) or "B" (treatment)
    - should_enable_ai: whether AI prioritization should be enabled
    """
    try:
        logger.info(f"[API] /experiments/assign → user_id={user_id}, exp_id={experiment_id}")
        
        from services.ab_test_service import get_ab_test_service
        ab_service = get_ab_test_service()
        
        group = ab_service.assign_group(user_id, experiment_id)
        should_enable = ab_service.should_enable_ai_prioritization(user_id, experiment_id)
        
        return {
            "user_id": user_id,
            "experiment_id": experiment_id,
            "group": group,
            "should_enable_ai_prioritization": should_enable,
            "description": "Control - No AI" if group == "A" else "Treatment - With AI"
        }
    except Exception as e:
        logger.error(f"[API] /experiments/assign error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/track-metric")
async def track_experiment_metric(
    metric: ExperimentMetricInput
):
    """
    Track a metric observation in an A/B test.
    
    Metrics examples:
    - completion_rate: 0.0-1.0 (% completed)
    - time_hours: hours to complete
    - success_rate: 0.0-1.0
    - csat: 1.0-5.0 (customer satisfaction)
    """
    try:
        logger.info(f"[API] /experiments/track-metric → {metric.experiment_id}/{metric.metric_name}")
        
        from services.ab_test_service import get_ab_test_service
        ab_service = get_ab_test_service()
        
        result = ab_service.track_metric(
            experiment_id=metric.experiment_id,
            user_id=metric.user_id,
            group=metric.group,
            metric_name=metric.metric_name,
            metric_value=metric.metric_value
        )
        
        return {
            "recorded": result["recorded"],
            "metric": metric.metric_name,
        }
    except Exception as e:
        logger.error(f"[API] /experiments/track-metric error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/analyze/{metric_name}")
async def analyze_experiment(
    experiment_id: str,
    metric_name: str
):
    """
    Analyze A/B test results for a specific metric.
    
    Returns:
    - Statistical analysis (t-test, p-value)
    - Effect size (Cohen's d)
    - Winner determination
    - Recommendation
    """
    try:
        logger.info(f"[API] /experiments/analyze → {experiment_id}/{metric_name}")
        
        from services.ab_test_service import get_ab_test_service
        ab_service = get_ab_test_service()
        
        result = ab_service.analyze_experiment(experiment_id, metric_name)
        
        return {
            "experiment_id": result.experiment_id,
            "metric_name": metric_name,
            "group_a": {
                "mean": result.group_a_mean,
                "count": result.group_a_count,
            },
            "group_b": {
                "mean": result.group_b_mean,
                "count": result.group_b_count,
                "confidence_interval_95": result.confidence_interval,
            },
            "statistics": {
                "t_statistic": result.t_statistic,
                "p_value": result.p_value,
                "is_significant": result.is_significant,
                "effect_size": result.effect_size,
            },
            "winner": result.winner,
            "recommendation": result.recommendation,
        }
    except Exception as e:
        logger.error(f"[API] /experiments/analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}/status")
async def get_experiment_status(experiment_id: str):
    """Get current status of an A/B test experiment."""
    try:
        logger.info(f"[API] /experiments/status → {experiment_id}")
        
        from services.ab_test_service import get_ab_test_service
        ab_service = get_ab_test_service()
        
        status = ab_service.get_experiment_status(experiment_id)
        
        return status
    except Exception as e:
        logger.error(f"[API] /experiments/status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Fairness & Bias Detection Endpoints
# ──────────────────────────────────────────────────────────────────────────────

class DemographicPredictionInput(BaseModel):
    """Input for recording predictions with demographic information."""
    task_id: str
    user_id: str
    predicted_success: bool
    actual_success: bool
    demographics: Dict[str, str]  # e.g., {"department": "eng", "experience": "senior"}


@router.post("/fairness/record-prediction")
async def record_fairness_prediction(
    data: DemographicPredictionInput
):
    """
    Record prediction with demographic information for fairness tracking.
    
    Used to monitor for algorithmic bias and discrimination.
    """
    try:
        logger.info(f"[API] /fairness/record-prediction → {data.task_id}")
        
        from services.bias_detection_service import get_bias_detection_service
        bias_service = get_bias_detection_service()
        
        result = bias_service.record_prediction_for_fairness(
            task_id=data.task_id,
            user_id=data.user_id,
            predicted_success=data.predicted_success,
            actual_success=data.actual_success,
            demographics=data.demographics
        )
        
        return {
            "recorded": result["recorded"],
            "task_id": data.task_id,
        }
    except Exception as e:
        logger.error(f"[API] /fairness/record-prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fairness/analyze/{demographic_attribute}")
async def analyze_fairness(
    demographic_attribute: str,
    window_days: int = Query(default=30, ge=7, le=365)
):
    """
    Analyze fairness and bias by demographic attribute.
    
    Args:
        demographic_attribute: e.g., "department", "experience_level", "region"
        window_days: Days of historical data to analyze (7-365)
    
    Returns:
    - Accuracy gaps between groups
    - Demographic parity analysis
    - Fairness alerts
    - Feature importances (via SHAP)
    """
    try:
        logger.info(f"[API] /fairness/analyze → {demographic_attribute}")
        
        from services.bias_detection_service import get_bias_detection_service
        bias_service = get_bias_detection_service()
        
        result = bias_service.analyze_demographic_parity(demographic_attribute, window_days)
        
        return {
            "attribute": demographic_attribute,
            "analysis_date": result.analysis_date.isoformat(),
            "groups": {
                name: {
                    "group_size": metrics.group_size,
                    "accuracy": f"{metrics.accuracy:.1%}",
                    "precision": f"{metrics.precision:.1%}",
                    "recall": f"{metrics.recall:.1%}",
                    "f1_score": f"{metrics.f1_score:.2f}",
                    "positive_rate": f"{metrics.positive_rate:.1%}",
                }
                for name, metrics in result.groups.items()
            },
            "accuracy_analysis": {
                "max_gap": f"{result.max_accuracy_gap:.1%}",
                "gap_groups": result.max_accuracy_gap_groups,
                "is_fair": result.accuracy_gap_is_fair,
                "threshold": f"{bias_service.accuracy_gap_threshold:.1%}",
            },
            "demographic_parity": {
                "max_gap": f"{result.demographic_parity_gap:.1%}",
                "is_fair": result.demographic_parity_is_fair,
                "threshold": f"{bias_service.demographic_parity_threshold:.1%}",
            },
            "alerts": [
                {
                    "metric": alert.metric_type.value,
                    "groups": [alert.group_a, alert.group_b],
                    "difference": f"{alert.difference:.1%}",
                    "recommendation": alert.recommendation,
                }
                for alert in result.alerts
            ],
            "feature_importances": result.feature_importances,
        }
    except Exception as e:
        logger.error(f"[API] /fairness/analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fairness/dashboard")
async def get_fairness_dashboard():
    """Get comprehensive fairness and bias dashboard."""
    try:
        logger.info("[API] /fairness/dashboard → collecting fairness metrics")
        
        from services.bias_detection_service import get_bias_detection_service
        bias_service = get_bias_detection_service()
        
        dashboard = bias_service.get_fairness_dashboard()
        
        return {
            "success": True,
            "data": dashboard
        }
    except Exception as e:
        logger.error(f"[API] /fairness/dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Multimodal Retrieval Endpoints
# ──────────────────────────────────────────────────────────────────────────────

class DocumentIngestionInput(BaseModel):
    """Input for document ingestion."""
    file_path: str
    metadata: Optional[Dict] = None


@router.post("/documents/ingest")
async def ingest_document(
    request: DocumentIngestionInput
):
    """
    Ingest a multimodal document (PDF, JPEG, PNG, TXT, Markdown).
    
    Process:
    1. Extract text from document
    2. Chunk into 256-token windows
    3. Generate embeddings (BAAI/bge-large-en-v1.5, 1024-dim)
    4. Store in MongoDB
    5. Optionally upsert to Pinecone
    
    Supported types: PDF, JPEG, PNG, TXT, Markdown
    """
    try:
        logger.info(f"[API] /documents/ingest → {request.file_path}")
        
        from services.multimodal_service import get_multimodal_retrieval
        retrieval = get_multimodal_retrieval()
        
        result = retrieval.ingest_document(request.file_path, request.metadata)
        
        return {
            "success": result.get("success"),
            "document": result.get("document"),
            "source_type": result.get("source_type"),
            "chunks_created": result.get("chunks_count"),
            "total_tokens": result.get("total_tokens"),
        }
    except Exception as e:
        logger.error(f"[API] /documents/ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/search")
async def search_documents(
    query: str = Body(...),
    method: str = Query(default="semantic", enum=["semantic", "keyword"]),
    top_k: int = Query(default=5, ge=1, le=20),
    source_type: Optional[str] = Query(None)
):
    """
    Search ingested documents.
    
    Methods:
    - semantic: Vector similarity search (default, requires embeddings)
    - keyword: Keyword matching (fast, no embeddings needed)
    
    Args:
        query: Search query text
        method: Search method (semantic or keyword)
        top_k: Number of results (1-20)
        source_type: Filter by source type (pdf, image, txt, markdown)
    """
    try:
        logger.info(f"[API] /documents/search → {query} ({method})")
        
        from services.multimodal_service import get_multimodal_retrieval
        retrieval = get_multimodal_retrieval()
        
        if method == "semantic":
            results = retrieval.retrieve_similar_chunks(query, top_k, source_type)
        else:
            results = retrieval.search_documents(query, top_k)
        
        return {
            "query": query,
            "method": method,
            "results_count": len(results),
            "results": [
                {
                    "chunk_id": r.get("chunk_id"),
                    "content": r.get("content")[:200],  # First 200 chars
                    "source_document": r.get("source_document"),
                    "source_type": r.get("source_type"),
                    "similarity": round(r.get("similarity", 0), 3) if method == "semantic" else None,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"[API] /documents/search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_name}/stats")
async def get_document_stats(document_name: str):
    """Get statistics about an ingested document."""
    try:
        logger.info(f"[API] /documents/stats → {document_name}")
        
        from services.multimodal_service import get_multimodal_retrieval
        retrieval = get_multimodal_retrieval()
        
        stats = retrieval.get_document_stats(document_name)
        
        return stats
    except Exception as e:
        logger.error(f"[API] /documents/stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Voice & Multilingual Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/voice/transcribe")
async def transcribe_audio(
    audio_data: bytes = Body(...),
    user_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None, enum=["en", "hi", "ta", "te", "kn", "mr"])
):
    """
    Transcribe audio to text with language detection.
    
    Supported languages:
    - en: English
    - hi: हिन्दी (Hindi)
    - ta: தமிழ் (Tamil)
    - te: తెలుగు (Telugu)
    - kn: ಕನ್ನಡ (Kannada)
    - mr: मराठी (Marathi)
    """
    try:
        logger.info(f"[API] /voice/transcribe → {user_id}")
        
        from services.voice_service import get_voice_service, Language
        
        voice_service = get_voice_service()
        
        # Parse language if provided
        lang = None
        if language:
            lang = Language(language)
        
        result = voice_service.process_audio_input(audio_data, user_id, lang)
        
        return result
    except Exception as e:
        logger.error(f"[API] /voice/transcribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/synthesize")
async def synthesize_speech(
    text: str = Body(...),
    language: str = Query(..., enum=["en", "hi", "ta", "te", "kn", "mr"]),
    user_id: Optional[str] = Query(None)
):
    """
    Convert text to speech in specified language.
    
    Returns: Audio file (MP3 format)
    """
    try:
        logger.info(f"[API] /voice/synthesize → {language}")
        
        from services.voice_service import get_voice_service, Language
        
        voice_service = get_voice_service()
        
        lang = Language(language)
        audio_data = voice_service.generate_audio_output(text, lang, user_id)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Text-to-speech synthesis failed")
        
        from fastapi.responses import StreamingResponse
        import io
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"[API] /voice/synthesize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/translate-and-speak")
async def translate_and_speak(
    text: str = Body(...),
    source_language: Optional[str] = Query(None),
    target_language: str = Query(..., enum=["en", "hi", "ta", "te", "kn", "mr"]),
    user_id: Optional[str] = Query(None)
):
    """
    Translate text (if needed) and generate speech in target language.
    
    Returns: Audio file (MP3 format)
    """
    try:
        logger.info(f"[API] /voice/translate-and-speak → {target_language}")
        
        from services.voice_service import get_voice_service, Language
        
        voice_service = get_voice_service()
        
        source_lang = Language(source_language) if source_language else None
        target_lang = Language(target_language)
        
        audio_data = voice_service.translate_and_speak(text, source_lang, target_lang)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Translation/synthesis failed")
        
        from fastapi.responses import StreamingResponse
        import io
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
    except Exception as e:
        logger.error(f"[API] /voice/translate-and-speak error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/languages")
async def get_supported_languages():
    """Get list of supported languages for voice interactions."""
    try:
        from services.voice_service import get_voice_service
        
        voice_service = get_voice_service()
        return voice_service.get_supported_languages()
    except Exception as e:
        logger.error(f"[API] /voice/languages error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/history/{user_id}")
async def get_voice_history(
    user_id: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get voice interaction history for a user."""
    try:
        logger.info(f"[API] /voice/history → {user_id}")
        
        from services.voice_service import get_voice_service
        
        voice_service = get_voice_service()
        history = voice_service.get_interaction_history(user_id, limit)
        
        return {
            "user_id": user_id,
            "interactions_count": len(history),
            "interactions": history,
        }
    except Exception as e:
        logger.error(f"[API] /voice/history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Security & Compliance Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/security/status")
async def get_security_status():
    """Get overall security status (rate limiting, key rotation, audit logging)."""
    try:
        logger.info("[API] /security/status → checking security status")
        
        from services.security_service import get_security_service
        security_service = get_security_service()
        
        status = security_service.get_security_status()
        
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"[API] /security/status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/audit-log")
async def get_audit_log(
    user_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=10, le=1000)
):
    """
    Get audit log entries for compliance and monitoring.
    
    Event types: api_call, auth, security, system
    """
    try:
        logger.info("[API] /security/audit-log → retrieving audit log")
        
        from services.security_service import get_security_service
        security_service = get_security_service()
        
        entries = security_service.centralized_logger.get_audit_log(
            user_id=user_id,
            event_type=event_type,
            limit=limit
        )
        
        return {
            "total_entries": len(entries),
            "entries": entries,
        }
    except Exception as e:
        logger.error(f"[API] /security/audit-log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/secrets/rotation-status")
async def get_rotation_status():
    """Get secret rotation status for all API keys."""
    try:
        logger.info("[API] /security/secrets/rotation-status → checking rotation")
        
        from services.security_service import get_security_service
        security_service = get_security_service()
        
        status = security_service.secret_manager.get_rotation_status()
        
        return {
            "secrets": status
        }
    except Exception as e:
        logger.error(f"[API] /security/secrets/rotation-status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


    try:
        db = get_db()
        # Quick check: ping collections
        collections = ["tasks", "verifications", "reasoning_traces"]
        for col in collections:
            db[col].count_documents({}, limit=1)
        
        return {
            "status": "healthy",
            "components": {
                "pipeline": "ready",
                "verification": "ready",
                "reasoning": "ready",
                "debate": "ready",
                "database": "connected",
            }
        }
    except Exception as e:
        logger.error(f"[API] /health error: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }, 503
