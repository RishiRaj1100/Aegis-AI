"""
MULTI-AGENT DEBATE SYSTEM (CRITICAL)
Three specialized agents debate before final decision.
- Optimistic Agent: Bullish forecast (85-95th percentile)
- Risk Agent: Conservative forecast (5-25th percentile)
- Execution Agent: Feasibility check
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json

from services.mongodb_service import get_db
from services.catalyst_service import get_catalyst_predictor

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent roles in the debate."""
    OPTIMISTIC = "optimistic"
    RISK = "risk"
    EXECUTION = "execution"


class DebateConsensus(str, Enum):
    """Level of agreement among agents."""
    STRONG_CONSENSUS = "strong_consensus"      # All within 15% of mean
    MODERATE_CONSENSUS = "moderate_consensus"  # All within 25% of mean
    CONFLICTED = "conflicted"                   # Wide disagreement


@dataclass
class AgentForecast:
    """Forecast from one agent."""
    agent_role: AgentRole
    success_probability: float  # [0, 1]
    reasoning: str
    risk_factors: List[str]
    recommendations: List[str]
    confidence: float  # [0, 1] in this forecast


@dataclass
class DebateResult:
    """Complete multi-agent debate result."""
    task_id: str
    task_description: str
    optimistic_forecast: AgentForecast
    risk_forecast: AgentForecast
    execution_forecast: AgentForecast
    central_forecast: float  # Mean of three forecasts
    consensus_level: DebateConsensus
    consensus_confidence: float  # [0, 1] how much we trust consensus
    conflicts: List[Dict]  # Where agents disagree
    final_recommendation: str
    timestamp: str


class OptimisticAgent:
    """
    Bullish perspective: assumes best-case scenarios, highlights opportunities.
    Forecast target: 85-95th percentile of distribution.
    """

    def __init__(self):
        self.name = "Optimistic Agent"
        self.role = AgentRole.OPTIMISTIC

    def analyze(
        self,
        task_description: str,
        task_features: Dict,
        similar_cases: List[Dict]
    ) -> AgentForecast:
        """Generate optimistic forecast."""
        logger.debug(f"[{self.name}] Analyzing task...")
        
        # Count best outcomes from similar cases
        best_outcomes = sum(
            1 for case in similar_cases
            if case.get("outcome", {}).get("success") is True
        )
        
        # Base forecast from best cases
        if similar_cases:
            best_case_rate = best_outcomes / len(similar_cases)
        else:
            best_case_rate = 0.5
        
        # Optimistic boost: assume we can replicate best conditions
        optimistic_prob = min(
            best_case_rate + 0.15,  # Add 15% boost
            0.95  # Cap at 95% to avoid overconfidence
        )
        
        risk_factors = []
        if task_features.get("complexity", 0.5) > 0.7:
            risk_factors.append("Task complexity")
        
        recommendations = [
            "Allocate best team members for this task",
            "Ensure clear requirements and communication",
            "Schedule daily check-ins to maintain momentum"
        ]
        
        reasoning = f"""
        ✓ Optimistic Perspective:
        • Best similar cases succeeded at {best_outcomes}/{len(similar_cases)}
        • With optimal team & resources: +15% probability boost
        • Final forecast: {optimistic_prob:.1%}
        
        Assumption: Everything goes right, team is experienced.
        """
        
        return AgentForecast(
            agent_role=self.role,
            success_probability=optimistic_prob,
            reasoning=reasoning.strip(),
            risk_factors=risk_factors,
            recommendations=recommendations,
            confidence=0.85  # Optimistic, but aware this is best-case
        )


class RiskAgent:
    """
    Conservative perspective: assumes worst-case scenarios, highlights blockers.
    Forecast target: 5-25th percentile of distribution.
    """

    def __init__(self):
        self.name = "Risk Agent"
        self.role = AgentRole.RISK

    def analyze(
        self,
        task_description: str,
        task_features: Dict,
        similar_cases: List[Dict]
    ) -> AgentForecast:
        """Generate conservative forecast."""
        logger.debug(f"[{self.name}] Analyzing task...")
        
        # Count worst outcomes from similar cases
        worst_outcomes = sum(
            1 for case in similar_cases
            if case.get("outcome", {}).get("success") is False
        )
        
        # Base forecast from worst cases
        if similar_cases:
            worst_case_rate = worst_outcomes / len(similar_cases)
        else:
            worst_case_rate = 0.5
        
        # Conservative: assume difficulties
        conservative_prob = max(
            worst_case_rate - 0.15,  # Subtract 15% for caution
            0.05  # Floor at 5% to avoid extreme pessimism
        )
        
        # Identify specific risks
        risk_factors = []
        if task_features.get("complexity", 0.5) > 0.7:
            risk_factors.append("High complexity: difficult to estimate/execute")
        if task_features.get("requires_team"):
            risk_factors.append("Team coordination overhead: communication delays, conflicts")
        if task_features.get("days_until_deadline", 30) < 7:
            risk_factors.append("Tight deadline: no buffer for unexpected issues")
        if task_features.get("estimated_effort_hours", 10) > 40:
            risk_factors.append("Long duration: higher chance of scope creep")
        
        recommendations = [
            "Add 50% buffer to timeline estimate",
            "Identify and mitigate top 3 blockers NOW",
            "Have backup plan for each critical step",
            "Schedule risk review meeting with stakeholders"
        ]
        
        reasoning = f"""
        ⚠️  Risk Perspective:
        • Worst similar cases failed at {worst_outcomes}/{len(similar_cases)}
        • Assuming typical issues arise: -15% probability adjustment
        • Final forecast: {conservative_prob:.1%}
        
        Key Risks: {', '.join(risk_factors) if risk_factors else 'None identified'}
        
        Assumption: Typical problems will occur (communication delays, scope creep, etc.)
        """
        
        return AgentForecast(
            agent_role=self.role,
            success_probability=conservative_prob,
            reasoning=reasoning.strip(),
            risk_factors=risk_factors,
            recommendations=recommendations,
            confidence=0.80  # Risk-aware, but not overly pessimistic
        )


class ExecutionAgent:
    """
    Feasibility perspective: can we actually do this given resources & constraints?
    Checks: resource availability, team capacity, technical feasibility.
    """

    def __init__(self):
        self.name = "Execution Agent"
        self.role = AgentRole.EXECUTION

    def analyze(
        self,
        task_description: str,
        task_features: Dict,
        similar_cases: List[Dict]
    ) -> AgentForecast:
        """Generate feasibility forecast."""
        logger.debug(f"[{self.name}] Analyzing task...")
        
        feasibility_score = 1.0  # Start at 100% feasible
        
        # Resource availability check
        if task_features.get("requires_team"):
            available_team = task_features.get("available_team_members", 0)
            required_team = task_features.get("required_team_members", 3)
            if available_team < required_team:
                feasibility_score *= 0.7  # 30% penalty
        
        # Capacity check
        team_current_load = task_features.get("team_load_percentage", 0)
        if team_current_load > 80:
            feasibility_score *= 0.8  # 20% penalty
        
        # Technical feasibility
        if task_features.get("has_blockers"):
            blocker_count = len(task_features.get("blockers", []))
            feasibility_score *= (1.0 - 0.1 * blocker_count)  # 10% per blocker
        
        # Skills/experience match
        if task_features.get("requires_new_skills"):
            feasibility_score *= 0.85  # 15% penalty for skill gap
        
        # Clamp to [0.2, 0.9] for execution feasibility
        execution_prob = min(max(feasibility_score * 0.8, 0.2), 0.9)
        
        blockers = []
        if task_features.get("requires_team"):
            if available_team < required_team:
                blockers.append(f"Insufficient team: {available_team} available, {required_team} required")
        if blockers:
            pass  # Already added above
        
        recommendations = []
        if team_current_load > 80:
            recommendations.append("Team is near capacity: consider postponing or adding resources")
        if task_features.get("requires_new_skills"):
            recommendations.append("Skills gap: plan for training/ramp-up time")
        if not blockers:
            recommendations.append("Execution is feasible with current resources")
        
        reasoning = f"""
        ⚡ Execution Feasibility:
        • Resource availability: {int(feasibility_score * 100)}% feasible
        • Team capacity utilization: {team_current_load:.0f}%
        • Technical blockers: {len(task_features.get('blockers', []))}
        • Final forecast: {execution_prob:.1%}
        
        Can we execute this?  {'✓ YES' if execution_prob > 0.6 else '✗ CHALLENGING'}
        """
        
        return AgentForecast(
            agent_role=self.role,
            success_probability=execution_prob,
            reasoning=reasoning.strip(),
            risk_factors=blockers,
            recommendations=recommendations,
            confidence=0.90  # High confidence in feasibility assessment
        )


class MultiAgentDebater:
    """
    Orchestrates debate between optimistic, risk, and execution agents.
    Provides consensus, conflicts, and final recommendation.
    """

    def __init__(self, db=None):
        self.db = db or get_db()
        self.debate_collection = self.db["multi_agent_debates"]
        
        self.optimistic_agent = OptimisticAgent()
        self.risk_agent = RiskAgent()
        self.execution_agent = ExecutionAgent()
        
        # Ensure indexes
        self.debate_collection.create_index("timestamp")
        self.debate_collection.create_index("task_id")

    def debate(
        self,
        task_id: str,
        task_description: str,
        task_features: Dict,
        similar_cases: List[Dict],
        user_id: Optional[str] = None
    ) -> DebateResult:
        """
        Run full multi-agent debate on a task.
        
        Returns:
            DebateResult with all forecasts, consensus, and final recommendation
        """
        logger.info(f"[MultiAgentDebater] Starting debate for task {task_id}")
        
        # Each agent analyzes the task
        optimistic = self.optimistic_agent.analyze(task_description, task_features, similar_cases)
        risk = self.risk_agent.analyze(task_description, task_features, similar_cases)
        execution = self.execution_agent.analyze(task_description, task_features, similar_cases)
        
        # Compute central forecast (mean of three)
        central_forecast = (
            optimistic.success_probability +
            risk.success_probability +
            execution.success_probability
        ) / 3
        
        # Determine consensus level
        forecasts = [
            optimistic.success_probability,
            risk.success_probability,
            execution.success_probability
        ]
        forecast_spread = max(forecasts) - min(forecasts)
        
        if forecast_spread <= 0.15:
            consensus_level = DebateConsensus.STRONG_CONSENSUS
            consensus_confidence = 0.95
        elif forecast_spread <= 0.25:
            consensus_level = DebateConsensus.MODERATE_CONSENSUS
            consensus_confidence = 0.80
        else:
            consensus_level = DebateConsensus.CONFLICTED
            consensus_confidence = 0.60
        
        # Identify specific conflicts
        conflicts = self._identify_conflicts(optimistic, risk, execution)
        
        # Generate final recommendation
        final_recommendation = self._generate_final_recommendation(
            central_forecast,
            consensus_level,
            conflicts,
            optimistic, risk, execution
        )
        
        result = DebateResult(
            task_id=task_id,
            task_description=task_description,
            optimistic_forecast=optimistic,
            risk_forecast=risk,
            execution_forecast=execution,
            central_forecast=central_forecast,
            consensus_level=consensus_level,
            consensus_confidence=consensus_confidence,
            conflicts=conflicts,
            final_recommendation=final_recommendation,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store debate result
        self._store_debate(result, user_id)
        
        return result

    def _identify_conflicts(
        self,
        optimistic: AgentForecast,
        risk: AgentForecast,
        execution: AgentForecast
    ) -> List[Dict]:
        """
        Identify specific dimensions where agents disagree.
        """
        conflicts = []
        
        # Check resource availability
        opt_res_ok = optimistic.success_probability > 0.75
        risk_res_ok = risk.success_probability > 0.5
        exec_res_ok = execution.success_probability > 0.6
        
        if not (opt_res_ok and risk_res_ok and exec_res_ok):
            conflicts.append({
                "dimension": "resource_availability",
                "optimistic_view": "Resources sufficient",
                "risk_view": "Resources tight",
                "execution_view": "Can work but risky"
            })
        
        # Check timeline feasibility
        if len(risk.risk_factors) > 0:
            conflicts.append({
                "dimension": "timeline_feasibility",
                "optimistic_view": "On schedule",
                "risk_view": f"Risk: {risk.risk_factors[0] if risk.risk_factors else 'unknown'}",
                "execution_view": "Feasible"
            })
        
        return conflicts

    def _generate_final_recommendation(
        self,
        central_forecast: float,
        consensus_level: DebateConsensus,
        conflicts: List[Dict],
        optimistic: AgentForecast,
        risk: AgentForecast,
        execution: AgentForecast
    ) -> str:
        """
        Generate final recommendation integrating all perspectives.
        """
        if central_forecast >= 0.8 and consensus_level == DebateConsensus.STRONG_CONSENSUS:
            return "✓ PROCEED: High success probability with strong agent consensus."
        
        elif central_forecast >= 0.7 and consensus_level in [DebateConsensus.STRONG_CONSENSUS, DebateConsensus.MODERATE_CONSENSUS]:
            mitigations = risk.recommendations[:2]  # Top 2 mitigations
            return f"✓ PROCEED with CAUTION: Moderate success probability. Mitigations: {'; '.join(mitigations)}"
        
        elif central_forecast >= 0.5 and execution.success_probability >= 0.6:
            return (
                f"⚠️  CONDITIONAL: Feasible ({execution.success_probability:.0%}) but risky ({risk.success_probability:.0%}). "
                f"Requires risk mitigation and close monitoring. Consider reducing scope."
            )
        
        else:
            return (
                f"✗ NOT RECOMMENDED: Low success probability ({central_forecast:.0%}). "
                f"Recommend re-scoping, breaking into smaller tasks, or postponing."
            )

    def _store_debate(self, result: DebateResult, user_id: Optional[str]):
        """Store debate result for audit."""
        try:
            doc = {
                "task_id": result.task_id,
                "task_description": result.task_description,
                "optimistic_forecast": result.optimistic_forecast.success_probability,
                "risk_forecast": result.risk_forecast.success_probability,
                "execution_forecast": result.execution_forecast.success_probability,
                "central_forecast": result.central_forecast,
                "consensus_level": result.consensus_level.value,
                "consensus_confidence": result.consensus_confidence,
                "conflict_count": len(result.conflicts),
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
            }
            self.debate_collection.insert_one(doc)
            logger.info(f"[MultiAgentDebater] Debate stored for task {result.task_id}")
        except Exception as e:
            logger.error(f"[MultiAgentDebater] Error storing debate: {e}")


# Singleton instance
_debater = None


def get_multi_agent_debater(db=None) -> MultiAgentDebater:
    """Get or create singleton MultiAgentDebater instance."""
    global _debater
    if _debater is None:
        _debater = MultiAgentDebater(db=db)
    return _debater
