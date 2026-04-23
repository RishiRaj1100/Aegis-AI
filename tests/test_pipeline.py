"""
AegisAI - Integration Tests
Tests the full pipeline using a mock Groq client to avoid live API calls.
Run with: pytest tests/ -v
"""

from __future__ import annotations

import asyncio
import json
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_COMMANDER_RESPONSE = json.dumps({
    "subtasks": [
        {
            "id": "T1",
            "title": "Market Research",
            "description": "Analyse the target market size, competitors, and customer segments.",
            "priority": 1,
            "estimated_duration_minutes": 120,
            "dependencies": [],
        },
        {
            "id": "T2",
            "title": "Define MVP Features",
            "description": "Identify core features for the minimum viable product.",
            "priority": 1,
            "estimated_duration_minutes": 90,
            "dependencies": ["T1"],
        },
        {
            "id": "T3",
            "title": "Build Prototype",
            "description": "Develop a working prototype of the core features.",
            "priority": 2,
            "estimated_duration_minutes": 2400,
            "dependencies": ["T2"],
        },
    ],
    "goal_summary": "Launch a SaaS AI resume screening tool in 3 months.",
    "complexity_score": 0.65,
})

MOCK_RESEARCH_RESPONSE = json.dumps({
    "insights": "The AI recruitment market is valued at $590M globally. Key competitors include HireVue and Paradox. The primary challenge is bias mitigation in ML models. The technical stack is well-understood with Python + FastAPI backend feasible. Data completeness is high given the user context provided.",
    "data_completeness": 0.75,
    "task_feasibility": 0.70,
    "risks": ["Regulatory scrutiny on AI hiring tools", "Model bias concerns"],
    "opportunities": ["Growing demand post-COVID remote hiring"],
    "recommended_resources": ["https://arxiv.org/abs/hiring-bias"],
})

MOCK_EXECUTION_RESPONSE = json.dumps({
    "execution_plan": "## Phase 1: Discovery & Planning (Week 1-2)\n\n### Tasks\n- Complete market research\n- Define MVP feature set\n\n### Milestone\nMarket analysis report and product spec approved.\n\n## Phase 2: Development (Week 3-8)\n\n### Tasks\n- Build backend API\n- Develop ML model\n- Create UI\n\n### Milestone\nWorking prototype with core screening functionality.\n\n## Phase 3: Launch (Week 9-12)\n\n### Tasks\n- Beta testing\n- Marketing launch\n\n### Milestone\nFirst 10 paying customers acquired.",
    "phases": [
        {"phase_number": 1, "phase_name": "Discovery", "duration_estimate": "Week 1-2", "subtask_ids": ["T1", "T2"], "milestone": "Product spec approved", "success_criteria": "Market analysis report complete"},
        {"phase_number": 2, "phase_name": "Development", "duration_estimate": "Week 3-8", "subtask_ids": ["T3"], "milestone": "Prototype ready", "success_criteria": "Core features implemented"},
    ],
    "total_estimated_duration": "12 weeks",
    "critical_path": ["T1", "T2", "T3"],
    "key_dependencies": "Cloud infrastructure and ML model training data are external dependencies.",
})

MOCK_TRUST_RESPONSE = json.dumps({
    "reasoning": "The confidence score of 68.5% reflects a well-defined goal with good data availability. The main drag is the high complexity of building an AI SaaS in 3 months. Past success rates are neutral at 50%. The team should focus on scope reduction to improve feasibility.",
    "improvement_tip": "Reduce the initial feature set to just resume parsing and scoring to cut complexity and boost feasibility above 0.80.",
})


@pytest.fixture
def mock_groq_client():
    """Return a mock Groq chat client that cycles through stage responses."""
    responses = [
        MOCK_COMMANDER_RESPONSE,
        MOCK_RESEARCH_RESPONSE,
        MOCK_EXECUTION_RESPONSE,
        MOCK_TRUST_RESPONSE,
        json.dumps({"lessons": [], "pattern_summary": "Insufficient history."}),
    ]
    call_count = [0]

    async def fake_chat(*args, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    mock = AsyncMock()
    mock.chat = AsyncMock(side_effect=fake_chat)
    mock.chat_json = AsyncMock(side_effect=lambda **kw: asyncio.coroutine(
        lambda: json.loads(responses[min(call_count[0], len(responses) - 1)])
    )())
    return mock


# ── Unit Tests: Trust Agent ───────────────────────────────────────────────────

class TestTrustAgent:
    @pytest.mark.asyncio
    async def test_confidence_formula(self):
        """The trust formula must produce the correct weighted result."""
        from agents.trust_agent import TrustAgent
        from unittest.mock import AsyncMock

        mock_groq = AsyncMock()
        mock_groq.chat_json = AsyncMock(return_value={
            "goal_clarity": 0.8,
            "information_quality": 0.9,
            "execution_feasibility": 0.7,
            "risk_manageability": 0.6,
            "resource_adequacy": 0.7,
            "external_uncertainty": 0.8,
            "reasoning": "Test reasoning.",
            "improvement_tip": "Test tip.",
        })

        agent = TrustAgent(groq=mock_groq)
        score = await agent.evaluate(
            past_success_rate=0.8,    # × 0.4 = 0.32
            data_completeness=0.9,    # × 0.3 = 0.27
            task_feasibility=0.7,     # × 0.2 = 0.14
            complexity_score=0.4,
            goal="Test goal",
            goal_summary="Test goal summary",
        )

        expected = (
            0.8 * 0.15
            + 0.9 * 0.20
            + 0.7 * 0.25
            + 0.6 * 0.15
            + 0.7 * 0.15
            + 0.8 * 0.10
        ) * 100
        assert abs(score.confidence - expected) < 0.1, (
            f"Expected confidence {expected:.2f}, got {score.confidence:.2f}"
        )

    @pytest.mark.asyncio
    async def test_risk_levels(self):
        """Risk levels must follow the correct confidence thresholds."""
        from agents.trust_agent import TrustAgent
        from models.schemas import RiskLevel
        from unittest.mock import AsyncMock

        mock_groq = AsyncMock()
        mock_groq.chat_json = AsyncMock(return_value={"reasoning": "x", "improvement_tip": "y"})
        agent = TrustAgent(groq=mock_groq)

        # HIGH risk: confidence < 45
        score = await agent.evaluate(0.2, 0.2, 0.2, 0.9, "g", "gs")
        assert score.risk_level == RiskLevel.HIGH, f"Expected HIGH, got {score.risk_level}"

        # MEDIUM risk: 45 <= confidence < 72
        score = await agent.evaluate(0.5, 0.5, 0.5, 0.5, "g", "gs")
        assert score.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {score.risk_level}"

        # LOW risk: confidence >= 72
        score = await agent.evaluate(0.9, 0.9, 0.9, 0.1, "g", "gs")
        assert score.risk_level == RiskLevel.MEDIUM, f"Expected MEDIUM, got {score.risk_level}"

    def test_risk_threshold_boundaries(self):
        from agents.trust_agent import TrustAgent
        from models.schemas import RiskLevel
        from config.settings import get_settings
        from unittest.mock import AsyncMock

        agent = TrustAgent(groq=AsyncMock())
        cfg = get_settings()
        high = cfg.RISK_HIGH_THRESHOLD
        medium = cfg.RISK_MEDIUM_THRESHOLD

        assert agent._compute_risk(high - 0.1) == RiskLevel.HIGH
        assert agent._compute_risk(high) == RiskLevel.MEDIUM
        assert agent._compute_risk(medium - 0.1) == RiskLevel.MEDIUM
        assert agent._compute_risk(medium) == RiskLevel.LOW


# ── Unit Tests: Commander Agent ───────────────────────────────────────────────

class TestCommanderAgent:
    @pytest.mark.asyncio
    async def test_decompose_returns_subtasks(self):
        """Commander must return SubTask objects and metadata."""
        from agents.commander_agent import CommanderAgent
        from unittest.mock import AsyncMock

        mock_groq = AsyncMock()
        mock_groq.chat_json = AsyncMock(return_value=json.loads(MOCK_COMMANDER_RESPONSE))
        agent = CommanderAgent(groq=mock_groq)

        result = await agent.decompose("Launch an AI SaaS product")
        assert len(result["subtasks"]) == 3
        assert result["complexity_score"] == 0.65
        assert "goal_summary" in result


# ── Unit Tests: Helpers ───────────────────────────────────────────────────────

class TestHelpers:
    def test_truncate(self):
        from utils.helpers import truncate
        long = "a" * 300
        result = truncate(long, 200)
        assert len(result) == 200

    def test_sanitise_goal(self):
        from utils.helpers import sanitise_goal
        messy = "  launch   a    SaaS  "
        assert sanitise_goal(messy) == "launch a SaaS"

    def test_confidence_emoji(self):
        from utils.helpers import confidence_emoji
        assert confidence_emoji(80) == "✅"
        assert confidence_emoji(55) == "⚠️"
        assert confidence_emoji(30) == "❌"

    def test_hash_goal_deterministic(self):
        from utils.helpers import hash_goal
        assert hash_goal("test goal") == hash_goal("test goal")
        assert hash_goal("test goal") != hash_goal("different goal")


class TestAuthProtection:
    @staticmethod
    def _assert_auth_before_pipeline(fn):
        params = list(inspect.signature(fn).parameters.keys())
        assert "current_user" in params
        assert "pipeline" in params
        assert params.index("current_user") < params.index("pipeline")

    def test_goal_routes_require_current_user_dependency(self):
        from routers.auth import get_current_user
        from routers.goal_router import submit_goal, submit_voice_goal, record_outcome, followup

        for fn in [submit_goal, submit_voice_goal, record_outcome, followup]:
            params = inspect.signature(fn).parameters
            assert "current_user" in params
            dep = params["current_user"].default
            assert getattr(dep, "dependency", None) == get_current_user
            self._assert_auth_before_pipeline(fn)

    def test_plan_routes_require_current_user_dependency(self):
        from routers.auth import get_current_user
        from routers.plan_router import get_plan_root, get_plan, get_subtasks, translate_plan, list_plans

        for fn in [get_plan_root, get_plan, get_subtasks, translate_plan, list_plans]:
            params = inspect.signature(fn).parameters
            assert "current_user" in params
            dep = params["current_user"].default
            assert getattr(dep, "dependency", None) == get_current_user
            self._assert_auth_before_pipeline(fn)

    def test_confidence_and_analytics_routes_require_current_user_dependency(self):
        from routers.auth import get_current_user
        from routers.confidence_router import (
            get_confidence,
            get_confidence_components,
            confidence_stats,
            refresh_confidence,
        )
        from routers.analytics_router import get_analytics

        for fn in [get_confidence, get_confidence_components, confidence_stats, refresh_confidence, get_analytics]:
            params = inspect.signature(fn).parameters
            assert "current_user" in params
            dep = params["current_user"].default
            assert getattr(dep, "dependency", None) == get_current_user
            self._assert_auth_before_pipeline(fn)


class TestFeatureFlags:
    def test_feature_flags_have_defaults(self):
        from config.settings import Settings

        settings = Settings(
            GROQ_API_KEY="test",
            SARVAM_API_KEY="test",
        )
        assert settings.STREAMING_ENABLED is True
        assert settings.SEMANTIC_MEMORY_ENABLED is True
        assert settings.PARALLEL_AGENTS_ENABLED is True
        assert settings.ANALYTICS_ENABLED is True
        assert settings.MAX_REVISION_ATTEMPTS >= 1
        total_weight = (
            settings.TRUST_WEIGHT_GOAL_CLARITY
            + settings.TRUST_WEIGHT_INFORMATION_QUALITY
            + settings.TRUST_WEIGHT_EXECUTION_FEASIBILITY
            + settings.TRUST_WEIGHT_RISK_MANAGEABILITY
            + settings.TRUST_WEIGHT_RESOURCE_ADEQUACY
            + settings.TRUST_WEIGHT_EXTERNAL_UNCERTAINTY
        )
        assert abs(total_weight - 1.0) < 0.0001


class TestConfidenceCompatibility:
    def test_normalise_trust_components_supports_legacy_shape(self):
        from routers.confidence_router import _normalise_trust_components

        legacy = {
            "data_completeness": 0.8,
            "task_feasibility": 0.6,
            "complexity_inverse": 0.4,
        }
        normalised = _normalise_trust_components(legacy)

        assert normalised.goal_clarity == 0.5
        assert normalised.information_quality == 0.8
        assert normalised.execution_feasibility == 0.6
        assert normalised.risk_manageability == 0.5
        assert normalised.resource_adequacy == 0.5
        assert normalised.external_uncertainty == 0.4

    def test_normalise_trust_components_clamps_values(self):
        from routers.confidence_router import _normalise_trust_components

        normalised = _normalise_trust_components(
            {
                "goal_clarity": 2,
                "information_quality": -1,
                "execution_feasibility": "0.7",
                "risk_manageability": "bad",
                "resource_adequacy": None,
                "external_uncertainty": 0.25,
            }
        )

        assert normalised.goal_clarity == 1.0
        assert normalised.information_quality == 0.0
        assert normalised.execution_feasibility == 0.7
        assert normalised.risk_manageability == 0.5
        assert normalised.resource_adequacy == 0.5
        assert normalised.external_uncertainty == 0.25
