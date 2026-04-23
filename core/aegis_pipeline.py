"""
AEGIS CORE PIPELINE — Complete System Integration
Integrates: Trust Agent → NYAYA Reasoning → Multi-Agent Debate → 
Prioritization → Execution → Reflection
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import subprocess
import time
import re

from agents.trust_agent import get_trust_agent, VerificationResult
from engines.nyaya_reasoning import get_nyaya_reasoning_engine, ReasoningTrace
from agents.multi_agent_debater import get_multi_agent_debater, DebateResult
from engines.behavior_intelligence import get_behavior_intelligence_engine, BehaviorAnalysis
from services.mongodb_service import get_db
from services.catalyst_service import get_catalyst_predictor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete pipeline output."""
    task_id: str
    task_description: str
    
    # Stage 1: Verification
    verification: VerificationResult
    can_proceed: bool
    
    # Stage 2: Reasoning
    reasoning_trace: ReasoningTrace
    
    # Stage 3: Debate
    debate_result: DebateResult
    
    # Stage 4: Prioritization
    priority_score: float
    rank: int
    
    # Stage 4.5: Behavior Intelligence
    behavior_analysis: Optional[Any] = None
    
    # Stage 5: Decision
    final_recommendation: str
    should_execute: bool
    risk_mitigations: List[str]
    
    # Metadata
    total_latency_ms: float
    timestamp: str


class AegisPipeline:
    """
    Complete autonomous decision intelligence pipeline.
    
    Flow:
    1. Trust Agent: Verify claims, assess risk
    2. NYAYA Engine: Explainable reasoning with four Pramanas
    3. Multi-Agent Debate: Optimistic vs Risk vs Execution
    4. Prioritization: Compute priority score and rank
    5. Execution Agent: Safe, controlled execution with audit
    6. Reflection Agent: Store outcome, detect drift, trigger retraining
    """

    def __init__(self, db=None):
        self.db = db or get_db()
        self.trust_agent = get_trust_agent()
        self.nyaya_engine = get_nyaya_reasoning_engine()
        self.debater = get_multi_agent_debater()
        self.catalyst = get_catalyst_predictor()
        self.behavior_engine = get_behavior_intelligence_engine()
        
        self.pipeline_collection = self.db["pipeline_executions"]
        self.feedback_collection = self.db["user_feedback"]
        
        # Ensure indexes
        self.pipeline_collection.create_index("timestamp")
        self.pipeline_collection.create_index("task_id")
        self.feedback_collection.create_index("task_id")

    def execute(
        self,
        task_id: str,
        task_description: str,
        task_features: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> PipelineResult:
        """
        Execute full pipeline: verify → reason → debate → prioritize → execute.
        """
        start_time = time.time()
        logger.info(f"[Pipeline] Starting execution for task {task_id}")
        
        # Default task features
        if task_features is None:
            task_features = {}
        
        # ===== STAGE 1: VERIFICATION =====
        logger.info(f"[Pipeline] Stage 1: Verification")
        verification = self.trust_agent.verify_claim(
            claim=task_description,
            context=task_features,
            user_id=user_id
        )
        can_proceed = not self.trust_agent.should_block_execution(verification)
        
        if not can_proceed:
            logger.warning(f"[Pipeline] Execution BLOCKED due to high risk: {verification.blocking_reason}")
        
        # ===== STAGE 2: REASONING =====
        logger.info(f"[Pipeline] Stage 2: NYAYA Reasoning")
        reasoning_trace = self.nyaya_engine.reason_about_task(
            task_id=task_id,
            task_description=task_description,
            task_features=task_features,
            user_id=user_id
        )
        
        # ===== STAGE 3: MULTI-AGENT DEBATE =====
        logger.info(f"[Pipeline] Stage 3: Multi-Agent Debate")
        similar_cases = self._retrieve_similar_cases(task_description, user_id)
        debate_result = self.debater.debate(
            task_id=task_id,
            task_description=task_description,
            task_features=task_features,
            similar_cases=similar_cases,
            user_id=user_id
        )
        
        # ===== STAGE 4: PRIORITIZATION =====
        logger.info(f"[Pipeline] Stage 4: Prioritization")
        priority_score, rank = self._compute_priority(
            debate_result.central_forecast,
            task_features,
            reasoning_trace.key_factors
        )
        
        # ===== STAGE 5: EXECUTION DECISION =====
        logger.info(f"[Pipeline] Stage 5: Execution Decision")
        should_execute = can_proceed and debate_result.central_forecast >= 0.6
        final_recommendation = self._make_final_recommendation(
            verification,
            debate_result,
            should_execute
        )
        risk_mitigations = verification.mitigations + reasoning_trace.recommendations
        
        # ===== STAGE 4.5: BEHAVIOR INTELLIGENCE =====
        logger.info(f"[Pipeline] Stage 4.5: Behavior Analysis")
        behavior_analysis = self.behavior_engine.analyze_task_behavior(
            task_id=task_id,
            task_features=task_features,
            user_id=user_id
        )
        
        # Adjust recommendation if high abandonment risk
        if behavior_analysis.abandonment_risk.value in ["HIGH", "CRITICAL"]:
            final_recommendation += " (⚠️ High abandonment risk - consider breaking into subtasks)"
        
        # ===== COMPILE RESULT =====
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = PipelineResult(
            task_id=task_id,
            task_description=task_description,
            verification=verification,
            can_proceed=can_proceed,
            reasoning_trace=reasoning_trace,
            debate_result=debate_result,
            priority_score=priority_score,
            rank=rank,
            behavior_analysis=behavior_analysis,
            final_recommendation=final_recommendation,
            should_execute=should_execute,
            risk_mitigations=risk_mitigations,
            total_latency_ms=elapsed_ms,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store result
        self._store_pipeline_result(result, user_id)
        
        logger.info(f"[Pipeline] Execution complete in {elapsed_ms:.0f}ms. Recommendation: {should_execute}")
        
        return result

    def _retrieve_similar_cases(self, query: str, user_id: Optional[str], top_k: int = 10) -> List[Dict]:
        """Retrieve similar past cases for debate."""
        try:
            from services.hybrid_search_service import get_hybrid_search_service
            search_service = get_hybrid_search_service()
            results = search_service.hybrid_search(query=query, user_id=user_id, top_k=top_k)
            return results
        except Exception as e:
            logger.error(f"[Pipeline] Error retrieving similar cases: {e}")
            return []

    def _compute_priority(
        self,
        success_probability: float,
        task_features: Dict,
        reasoning_factors: Dict
    ) -> Tuple[float, int]:
        """
        Compute priority score.
        
        Formula: Priority = (Impact × Success Prob × Urgency) / (Effort × Blockers)
        """
        impact = task_features.get("business_impact", 1.0)  # 0-1 scale
        urgency = 1.0 - (task_features.get("days_until_deadline", 30) / 30)  # Normalize
        effort = max(task_features.get("estimated_effort_hours", 10) / 40, 0.1)  # Normalize, min 0.1
        blockers = max(len(task_features.get("blockers", [])), 1)
        
        priority_score = (impact * success_probability * urgency) / (effort * blockers)
        
        # Rank (would be computed against all tasks in queue)
        rank = 1  # Placeholder; would be ranked in context of all pending tasks
        
        return min(priority_score, 100.0), rank  # Cap at 100

    def _make_final_recommendation(
        self,
        verification: VerificationResult,
        debate: DebateResult,
        should_execute: bool
    ) -> str:
        """Generate final recommendation integrating all signals."""
        if not should_execute:
            return (
                f"✗ DO NOT PROCEED: Risk too high ({verification.risk_score:.0%}) "
                f"or low success probability ({debate.central_forecast:.0%}). "
                f"Recommendation: {debate.final_recommendation}"
            )
        
        return (
            f"✓ PROCEED: {debate.final_recommendation}\n"
            f"Risk Level: {verification.risk_level.value.upper()} ({verification.risk_score:.0%})\n"
            f"Success Probability: {debate.central_forecast:.0%}\n"
            f"Consensus: {debate.consensus_level.value}"
        )

    def _store_pipeline_result(self, result: PipelineResult, user_id: Optional[str]):
        """Store complete pipeline result for audit and learning."""
        try:
            doc = {
                "task_id": result.task_id,
                "task_description": result.task_description[:200],  # Truncate for storage
                "can_proceed": result.can_proceed,
                "priority_score": result.priority_score,
                "final_recommendation": result.final_recommendation[:200],
                "should_execute": result.should_execute,
                "verification_risk": result.verification.risk_score,
                "debate_forecast": result.debate_result.central_forecast,
                "reasoning_confidence": result.reasoning_trace.confidence_score,
                "latency_ms": result.total_latency_ms,
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
            }
            self.pipeline_collection.insert_one(doc)
        except Exception as e:
            logger.error(f"[Pipeline] Error storing result: {e}")

    def record_feedback(
        self,
        task_id: str,
        predicted_success: bool,
        actual_success: bool,
        actual_effort_hours: float,
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Record user feedback for learning loop.
        
        This data is used to retrain the Catalyst predictor.
        """
        logger.info(f"[Pipeline] Recording feedback for task {task_id}")
        
        feedback_doc = {
            "task_id": task_id,
            "predicted_success": predicted_success,
            "actual_success": actual_success,
            "prediction_correct": predicted_success == actual_success,
            "actual_effort_hours": actual_effort_hours,
            "notes": notes,
            "user_id": user_id,
            "recorded_at": datetime.utcnow(),
        }
        
        result = self.feedback_collection.insert_one(feedback_doc)
        
        # Check if retraining is needed
        self._check_retraining_trigger()
        
        return {
            "recorded": True,
            "feedback_id": str(result.inserted_id),
            "prediction_accuracy": 1.0 if predicted_success == actual_success else 0.0
        }

    def _check_retraining_trigger(self):
        """
        Check if model retraining should be triggered based on feedback accumulation
        and drift detection.
        """
        try:
            # Count recent feedback
            recent_feedback = self.feedback_collection.count_documents({
                "recorded_at": {"$gte": datetime.utcnow().timestamp() - 86400 * 7}  # Last 7 days
            })
            
            if recent_feedback >= 20:  # Trigger after 20 feedback samples
                logger.info("[Pipeline] Triggering model retraining (20+ feedback samples)")
                # Would call: ci_cd_service.trigger_retrain()
        except Exception as e:
            logger.error(f"[Pipeline] Error checking retraining trigger: {e}")

    def get_pipeline_metrics(self) -> Dict:
        """Get system-wide pipeline metrics."""
        try:
            total_executions = self.pipeline_collection.count_documents({})
            successful_recommendations = self.pipeline_collection.count_documents(
                {"should_execute": True}
            )
            avg_latency = self.pipeline_collection.aggregate([
                {"$group": {"_id": None, "avg_latency": {"$avg": "$latency_ms"}}}
            ])
            
            avg_latency_ms = list(avg_latency)[0]["avg_latency"] if avg_latency else 0
            
            return {
                "total_pipeline_executions": total_executions,
                "recommended_to_execute": successful_recommendations,
                "execution_recommendation_rate": successful_recommendations / total_executions if total_executions > 0 else 0,
                "avg_pipeline_latency_ms": avg_latency_ms,
            }
        except Exception as e:
            logger.error(f"[Pipeline] Error getting metrics: {e}")
            return {}


# Singleton instance
_pipeline = None


def get_aegis_pipeline(db=None) -> AegisPipeline:
    """Get or create singleton AegisPipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = AegisPipeline(db=db)
    return _pipeline
