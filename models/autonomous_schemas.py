"""Schemas for the autonomous decision intelligence API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class AgentIOEnvelope(BaseModel):
    """Standardized agent contract for independent testing and tracing."""

    agent: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalyzeTaskRequest(BaseModel):
    task: str = Field(min_length=5, max_length=4000)
    language: str = Field(default="en-IN")
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class DebateRequest(BaseModel):
    task: str = Field(min_length=5, max_length=4000)
    context: Dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    task_id: str
    predicted_success: float = Field(ge=0.0, le=1.0)
    actual_outcome: Literal["success", "failed"]
    notes: Optional[str] = None


class SimilarTaskItem(BaseModel):
    task: str
    outcome: str
    similarity: float = Field(ge=0.0, le=1.0)


class ModelOutputs(BaseModel):
    xgboost_probability: float = Field(ge=0.0, le=1.0)
    logistic_delay: float = Field(ge=0.0, le=1.0)


class SystemTraceItem(BaseModel):
    step: str
    details: Dict[str, Any] = Field(default_factory=dict)


class FinalDecisionResponse(BaseModel):
    task_id: str
    success_probability: float = Field(ge=0.0, le=1.0)
    delay_risk: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reasoning: str
    reasoning_provider: Optional[str] = None
    fallback_used: bool = False
    system_confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    priority_score: float = Field(ge=0.0)
    model_outputs: ModelOutputs
    similar_tasks: List[SimilarTaskItem] = Field(default_factory=list)
    debate: Dict[str, Any] = Field(default_factory=dict)
    execution_plan: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    trust_analysis: Dict[str, Any] = Field(default_factory=dict)
    explainability: Dict[str, Any] = Field(default_factory=dict)
    execution_graph: Dict[str, Any] = Field(default_factory=dict)
    system_trace: List[SystemTraceItem] = Field(default_factory=list)
    traces: List[AgentIOEnvelope] = Field(default_factory=list)


class DebateResponse(BaseModel):
    optimist: str
    risk: str
    executor: str
    final_decision: str
    confidence: float = Field(ge=0.0, le=1.0)


class FeedbackResponse(BaseModel):
    accepted: bool
    retrain_triggered: bool
    samples_count: int


class ExplainabilityResponse(BaseModel):
    task_id: str
    shap_values: Dict[str, float] = Field(default_factory=dict)
    positive_factors: List[str] = Field(default_factory=list)
    negative_factors: List[str] = Field(default_factory=list)


class SimilarTasksResponse(BaseModel):
    task_id: Optional[str] = None
    tasks: List[SimilarTaskItem] = Field(default_factory=list)


class ModelStatusResponse(BaseModel):
    status: Literal["idle", "running"]
    last_run: Optional[str] = None
    samples_collected: int = Field(ge=0)
    threshold: int = Field(ge=1)
    next_trigger_in: int = Field(ge=0)
