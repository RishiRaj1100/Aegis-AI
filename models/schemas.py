"""
AegisAI - Pydantic Schemas & Domain Models
All request / response contracts and internal data structures live here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════════════════

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InputModality(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class SupportedLanguage(str, Enum):
    EN = "en-IN"
    HI = "hi-IN"
    BN = "bn-IN"
    TA = "ta-IN"
    TE = "te-IN"
    KN = "kn-IN"
    ML = "ml-IN"
    MR = "mr-IN"
    GU = "gu-IN"
    PA = "pa-IN"


# ═══════════════════════════════════════════════════════════════════════════════
# Sub-task Schema
# ═══════════════════════════════════════════════════════════════════════════════

class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    priority: int = Field(ge=1, le=5, default=3)
    estimated_duration_minutes: Optional[int] = None
    dependencies: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Trust / Confidence Components
# ═══════════════════════════════════════════════════════════════════════════════

class TrustComponents(BaseModel):
    """Six holistic dimensions assessed by the Trust Agent."""
    goal_clarity: float = Field(ge=0.0, le=1.0, description="How clear and specific the goal is")
    information_quality: float = Field(ge=0.0, le=1.0, description="Completeness and reliability of research data")
    execution_feasibility: float = Field(ge=0.0, le=1.0, description="Real-world achievability of the execution plan")
    risk_manageability: float = Field(ge=0.0, le=1.0, description="How controllable the identified risks are")
    resource_adequacy: float = Field(ge=0.0, le=1.0, description="Whether time, capital, and people are sufficient")
    external_uncertainty: float = Field(ge=0.0, le=1.0, description="Stability of the environment around the goal")


class TrustScore(BaseModel):
    confidence: float = Field(ge=0.0, le=100.0, description="Overall confidence 0-100")
    risk_level: RiskLevel
    components: TrustComponents
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════════
# Request Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class GoalRequest(BaseModel):
    """POST /goal — text-based goal submission."""
    goal: str = Field(min_length=5, max_length=2000, description="User goal in natural language")
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra context KV")
    modality: InputModality = Field(default=InputModality.TEXT)

    @field_validator("goal")
    @classmethod
    def goal_must_not_be_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 5:
            raise ValueError(
                "Goal must contain at least 5 non-whitespace characters."
            )
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "goal": "Launch a SaaS product for AI-based resume screening within 3 months",
                "language": "en-IN",
                "context": {"budget": "50000 USD", "team_size": 4},
                "modality": "text",
            }
        }
    )


class WorkflowDslRequest(BaseModel):
    workflow: str = Field(min_length=3, max_length=10000, description="Simple workflow DSL or arrow notation")
    title: str = Field(default="Workflow", max_length=120)


class OutcomePredictionRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)


class SimulationRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=2000)
    context: Optional[Dict[str, Any]] = None
    scenario: str = Field(default="baseline", max_length=120)


class ModelRegistryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=500)
    status: str = Field(default="active", max_length=30)


class ManualOverrideRequest(BaseModel):
    task_id: str = Field(min_length=1)
    decision: str = Field(pattern="^(approve|review|reject)$")
    notes: Optional[str] = Field(default=None, max_length=1000)


class VoiceGoalRequest(BaseModel):
    """POST /goal/voice — voice audio will be Base64-encoded."""
    audio_base64: str = Field(description="Base64-encoded audio bytes (WAV/MP3/WebM)", min_length=10)
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)
    audio_format: str = Field(default="webm", description="Audio container format: webm, wav, mp3, etc.")
    context: Optional[Dict[str, Any]] = None

    @field_validator("audio_base64")
    @classmethod
    def audio_must_not_exceed_size_limit(cls, v: str) -> str:
        # Base64 is ~4/3 of raw bytes. Limit raw audio to ~10 MB.
        max_b64_chars = 10 * 1024 * 1024 * 4 // 3
        if len(v) > max_b64_chars:
            raise ValueError("Audio payload exceeds the 10 MB limit.")
        return v


class PlanQueryParams(BaseModel):
    task_id: UUID
    translate_to: Optional[SupportedLanguage] = None


class ConfidenceQueryParams(BaseModel):
    task_id: UUID


class OutcomeUpdateRequest(BaseModel):
    task_id: UUID
    status: TaskStatus
    outcome_notes: Optional[str] = None
    actual_duration_minutes: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Response Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class SubTaskResponse(BaseModel):
    id: str
    title: str
    description: str
    priority: int
    estimated_duration_minutes: Optional[int]
    dependencies: List[str]


class PlanResponse(BaseModel):
    task_id: str
    goal: str
    subtasks: List[SubTaskResponse]
    research_insights: str
    execution_plan: str
    opportunities: List[str] = Field(default_factory=list)
    recommended_resources: List[str] = Field(default_factory=list)
    confidence: float
    risk_level: RiskLevel
    components: Optional[TrustComponents] = None
    reasoning: str
    spoken_summary: Optional[str] = None
    language: str
    created_at: datetime


class ConfidenceResponse(BaseModel):
    task_id: str
    confidence: float
    risk_level: RiskLevel
    components: TrustComponents
    reasoning: str
    updated_at: datetime


class GoalResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    plan: Optional[PlanResponse] = None
    audio_response_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded TTS audio when voice modality is requested",
    )


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Internal Memory / DB Documents
# ═══════════════════════════════════════════════════════════════════════════════

class TaskDocument(BaseModel):
    """MongoDB document stored for every processed goal."""
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    goal: str
    language: str
    subtasks: List[Dict[str, Any]] = Field(default_factory=list)
    research_insights: str = ""
    execution_plan: str = ""
    opportunities: List[str] = Field(default_factory=list)
    recommended_resources: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    risk_level: str = RiskLevel.MEDIUM.value
    trust_components: Dict[str, float] = Field(default_factory=dict)
    reasoning: str = ""
    spoken_summary: str = ""
    status: str = TaskStatus.PENDING.value
    outcome_notes: Optional[str] = None
    actual_duration_minutes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReflectionDocument(BaseModel):
    """Stored reflection snapshot used by the Reflection Agent."""
    reflection_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    previous_confidence: float
    updated_confidence: float
    lesson: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Follow-up schemas ─────────────────────────────────────────────────────────

class FollowUpRequest(BaseModel):
    """Follow-up question or voice message about an existing task."""
    task_id: str = Field(..., description="The task_id returned from POST /goal")
    message: str = Field(
        default="",
        max_length=2000,
        description="Text follow-up question (leave empty if sending audio)",
    )
    language: SupportedLanguage = Field(
        default=SupportedLanguage.EN,
        description="Language for the reply and TTS audio",
    )
    audio_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded audio of a spoken follow-up question",
    )
    audio_format: str = Field(default="webm", description="Audio container format: webm, wav, mp3, etc.")

    @field_validator("message")
    @classmethod
    def message_or_audio_required(cls, v: str, info: Any) -> str:
        # actual cross-field check done in router; this just strips whitespace
        return v.strip()

    @field_validator("audio_base64")
    @classmethod
    def audio_size_limit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        max_b64 = 10 * 1024 * 1024 * 4 // 3
        if len(v) > max_b64:
            raise ValueError("Audio payload exceeds the 10 MB limit.")
        return v


class FollowUpResponse(BaseModel):
    """Response to a follow-up question."""
    task_id: str
    reply: str
    language: str
    audio_base64: Optional[str] = None


class ExecutionGraphNode(BaseModel):
    id: str
    label: str
    type: str = "task"
    status: str = "pending"


class ExecutionGraphEdge(BaseModel):
    source: str
    target: str
    label: str = "depends_on"


class ExecutionGraphResponse(BaseModel):
    task_id: str
    goal: str
    nodes: List[ExecutionGraphNode]
    edges: List[ExecutionGraphEdge]
    mermaid: str


class SimilarTaskResponse(BaseModel):
    task_id: str
    goal: str
    confidence: float
    risk_level: str
    similarity: float
    status: str


class StrategyProfileResponse(BaseModel):
    user_id: Optional[str] = None
    profile_name: str
    strengths: List[str]
    watchouts: List[str]
    preferred_approach: str
    success_rate: float
    average_confidence: float
    recent_domains: List[str]


class OutcomePredictionResponse(BaseModel):
    task_id: Optional[str] = None
    predicted_success_probability: float
    predicted_risk_level: RiskLevel
    confidence_band: str
    human_review_required: bool
    likely_failure_modes: List[str]
    recommended_safeguards: List[str]
    rationale: str


class SimulationResponse(BaseModel):
    scenario: str
    predicted_confidence: float
    predicted_risk_level: RiskLevel
    success_probability: float
    bottlenecks: List[str]
    mitigation_steps: List[str]


class IntelligenceModelRecord(BaseModel):
    model_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    version: str
    description: str = ""
    status: str = "active"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DriftReportResponse(BaseModel):
    drift_score: float
    baseline_confidence: float
    recent_confidence: float
    baseline_success_rate: float
    recent_success_rate: float
    retraining_recommended: bool
    notes: List[str]


class IntelligenceOverviewResponse(BaseModel):
    total_tasks: int
    total_models: int
    total_reports: int
    active_model: Optional[str] = None
    average_confidence: float
    recent_success_rate: float
    drift_score: float
    scheduled_reflection_status: str
    human_review_queue_size: int


class ReflectionReportResponse(BaseModel):
    generated_at: datetime
    lessons: List[str]
    pattern_summary: str
    confidence_calibration_note: str
    suggested_weight_adjustments: Dict[str, float] = Field(default_factory=dict)
    updated_confidence_bias: float = 0.0


class ExecutionGraphNode(BaseModel):
    id: str
    label: str
    type: str = "task"
    status: str = "pending"


class ExecutionGraphEdge(BaseModel):
    source: str
    target: str
    label: str = "depends_on"


class ExecutionGraphResponse(BaseModel):
    task_id: str
    goal: str
    nodes: List[ExecutionGraphNode]
    edges: List[ExecutionGraphEdge]
    mermaid: str


class SimilarTaskResponse(BaseModel):
    task_id: str
    goal: str
    confidence: float
    risk_level: str
    similarity: float
    status: str


class StrategyProfileResponse(BaseModel):
    user_id: Optional[str] = None
    profile_name: str
    strengths: List[str]
    watchouts: List[str]
    preferred_approach: str
    success_rate: float
    average_confidence: float
    recent_domains: List[str]


class OutcomePredictionResponse(BaseModel):
    task_id: Optional[str] = None
    predicted_success_probability: float
    predicted_risk_level: RiskLevel
    confidence_band: str
    human_review_required: bool
    likely_failure_modes: List[str]
    recommended_safeguards: List[str]
    rationale: str


class SimulationResponse(BaseModel):
    scenario: str
    predicted_confidence: float
    predicted_risk_level: RiskLevel
    success_probability: float
    bottlenecks: List[str]
    mitigation_steps: List[str]


class IntelligenceModelRecord(BaseModel):
    model_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    version: str
    description: str = ""
    status: str = "active"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DriftReportResponse(BaseModel):
    drift_score: float
    baseline_confidence: float
    recent_confidence: float
    baseline_success_rate: float
    recent_success_rate: float
    retraining_recommended: bool
    notes: List[str]


class IntelligenceOverviewResponse(BaseModel):
    total_tasks: int
    total_models: int
    total_reports: int
    active_model: Optional[str] = None
    average_confidence: float
    recent_success_rate: float
    drift_score: float
    scheduled_reflection_status: str
    human_review_queue_size: int


class ReflectionReportResponse(BaseModel):
    generated_at: datetime
    lessons: List[str]
    pattern_summary: str
    confidence_calibration_note: str
    suggested_weight_adjustments: Dict[str, float] = Field(default_factory=dict)
    updated_confidence_bias: float = 0.0
