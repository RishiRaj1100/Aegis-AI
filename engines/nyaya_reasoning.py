"""
NYAYA REASONING ENGINE — Explainable Logic Framework
Implements NYAYA-style reasoning: Pratyaksha (direct), Anumana (inference),
Upamana (analogy), Sabda (authority/historical).
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json

from services.mongodb_service import get_db
from services.hybrid_search_service import get_hybrid_search_service

logger = logging.getLogger(__name__)


class PramanaType(str, Enum):
    """Types of valid evidence in NYAYA framework."""
    PRATYAKSHA = "pratyaksha"      # Direct observation/retrieval
    ANUMANA = "anumana"            # Inference/deduction
    UPAMANA = "upamana"            # Analogy/similar cases
    SABDA = "sabda"                # Authority/historical data


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    pramana: PramanaType  # Type of evidence
    premise: str  # The statement
    conclusion: str  # What we conclude from it
    confidence: float  # [0, 1]
    supporting_evidence: List[Dict]  # Retrieved cases or facts


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for a task."""
    task_id: str
    task_description: str
    reasoning_chain: List[ReasoningStep]
    key_factors: Dict[str, float]  # Factor name → impact score
    similar_cases: List[Dict]
    final_prediction: float  # [0, 1] success probability
    confidence_score: float  # [0, 1] confidence in prediction
    recommendations: List[str]
    timestamp: str


class NyayaReasoningEngine:
    """
    Implements NYAYA-style reasoning for explainable task success prediction.
    
    Uses four types of Pramanas (valid knowledge sources):
    1. Pratyaksha: Direct observation (current task features)
    2. Anumana: Inference (logical deduction from patterns)
    3. Upamana: Analogy (similar past cases)
    4. Sabda: Authority (historical data, best practices)
    """

    def __init__(self, db=None, search_service=None):
        self.db = db or get_db()
        self.search_service = search_service or get_hybrid_search_service()
        self.reasoning_collection = self.db["reasoning_traces"]
        self.case_collection = self.db["tasks"]  # Historical task outcomes
        
        # Ensure indexes
        self.reasoning_collection.create_index("timestamp")
        self.reasoning_collection.create_index("task_id")

    def reason_about_task(
        self,
        task_id: str,
        task_description: str,
        task_features: Dict,
        user_id: Optional[str] = None
    ) -> ReasoningTrace:
        """
        Apply NYAYA reasoning to predict task success.
        
        Args:
            task_id: Unique task identifier
            task_description: Natural language task description
            task_features: Extracted features (complexity, resources, etc.)
            user_id: Who requested this reasoning
            
        Returns:
            ReasoningTrace with full reasoning chain and prediction
        """
        logger.info(f"[NyayaEngine] Reasoning about task: {task_id}")
        
        reasoning_chain = []
        all_factors = {}
        
        # STEP 1: PRATYAKSHA (Direct Observation)
        # Extract directly observable features from current task
        pratyaksha_step = self._pratyaksha_analysis(task_description, task_features)
        reasoning_chain.append(pratyaksha_step)
        all_factors.update(pratyaksha_step.supporting_evidence[0].get("factors", {}))
        
        # STEP 2: UPAMANA (Analogy)
        # Retrieve and analyze similar past cases
        similar_cases = self._retrieve_similar_cases(task_description, user_id)
        upamana_step = self._upamana_analysis(similar_cases)
        reasoning_chain.append(upamana_step)
        all_factors.update(upamana_step.supporting_evidence[0].get("factors", {}))
        
        # STEP 3: ANUMANA (Inference)
        # Logical deduction from patterns
        anumana_step = self._anumana_inference(all_factors, task_features)
        reasoning_chain.append(anumana_step)
        all_factors.update(anumana_step.supporting_evidence[0].get("factors", {}))
        
        # STEP 4: SABDA (Authority)
        # Apply historical best practices
        sabda_step = self._sabda_analysis(task_features, similar_cases)
        reasoning_chain.append(sabda_step)
        all_factors.update(sabda_step.supporting_evidence[0].get("factors", {}))
        
        # STEP 5: Aggregate predictions and confidence
        final_prediction, confidence = self._aggregate_predictions(reasoning_chain)
        
        # STEP 6: Generate recommendations
        recommendations = self._generate_recommendations(all_factors, final_prediction)
        
        trace = ReasoningTrace(
            task_id=task_id,
            task_description=task_description,
            reasoning_chain=reasoning_chain,
            key_factors=all_factors,
            similar_cases=similar_cases[:3],  # Top 3 for display
            final_prediction=final_prediction,
            confidence_score=confidence,
            recommendations=recommendations,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store reasoning trace for audit
        self._store_reasoning_trace(trace, user_id)
        
        return trace

    def _pratyaksha_analysis(
        self,
        task_description: str,
        task_features: Dict
    ) -> ReasoningStep:
        """
        PRATYAKSHA: Direct observation of current task.
        
        Extract directly measurable features:
        - Complexity (low/medium/high)
        - Estimated effort (hours)
        - Required resources
        - Deadline pressure
        """
        logger.debug("[Pratyaksha] Analyzing direct task features")
        
        factors = {}
        evidence = []
        
        # Complexity assessment (keyword-based heuristic)
        complexity_keywords = {
            "trivial": 0.1,
            "simple": 0.2,
            "moderate": 0.5,
            "complex": 0.8,
            "very complex": 0.95,
        }
        
        desc_lower = task_description.lower()
        complexity = 0.5  # default
        for keyword, score in complexity_keywords.items():
            if keyword in desc_lower:
                complexity = score
                break
        
        factors["complexity"] = complexity
        evidence.append({
            "type": "direct_observation",
            "metric": "complexity",
            "value": complexity,
            "reasoning": f"Inferred from task description keywords"
        })
        
        # Effort estimation (heuristic: longer description = more complex)
        word_count = len(task_description.split())
        estimated_effort_hours = min(word_count / 50 * 2, 40)  # Rough heuristic
        
        factors["estimated_effort_hours"] = estimated_effort_hours
        evidence.append({
            "type": "direct_observation",
            "metric": "estimated_effort",
            "value": estimated_effort_hours,
            "reasoning": "Estimated from task description length"
        })
        
        # Resource requirements (from task_features)
        if task_features.get("requires_team"):
            factors["team_required"] = 1.0
            factors["coordination_overhead"] = 0.2
            evidence.append({
                "type": "direct_observation",
                "metric": "team_required",
                "value": True,
                "reasoning": "Task explicitly requires team collaboration"
            })
        
        # Deadline urgency
        if task_features.get("days_until_deadline"):
            days_left = task_features["days_until_deadline"]
            urgency = 1.0 - (days_left / max(days_left, 30))  # Normalize to [0, 1]
            factors["deadline_urgency"] = urgency
            evidence.append({
                "type": "direct_observation",
                "metric": "deadline_urgency",
                "value": urgency,
                "reasoning": f"{days_left} days left"
            })
        
        return ReasoningStep(
            step_number=1,
            pramana=PramanaType.PRATYAKSHA,
            premise="Direct observation of task features",
            conclusion=f"Task has complexity {complexity:.2f} and estimated effort {estimated_effort_hours:.1f}h",
            confidence=0.95,  # High confidence in direct observation
            supporting_evidence=[{"factors": factors, "observations": evidence}]
        )

    def _retrieve_similar_cases(
        self,
        task_description: str,
        user_id: Optional[str],
        top_k: int = 10
    ) -> List[Dict]:
        """Retrieve similar past tasks for analogy."""
        try:
            results = self.search_service.semantic_search(
                query=task_description,
                user_id=user_id,
                top_k=top_k
            )
            logger.debug(f"[Upamana] Retrieved {len(results)} similar cases")
            return results
        except Exception as e:
            logger.error(f"[Upamana] Error retrieving similar cases: {e}")
            return []

    def _upamana_analysis(self, similar_cases: List[Dict]) -> ReasoningStep:
        """
        UPAMANA: Reasoning by analogy from similar past cases.
        
        Logic:
        - If similar cases succeeded → positive factor
        - If similar cases failed → negative factor
        - Similarity score weights the evidence
        """
        logger.debug("[Upamana] Analyzing similar cases")
        
        factors = {}
        evidence = []
        
        if not similar_cases:
            return ReasoningStep(
                step_number=2,
                pramana=PramanaType.UPAMANA,
                premise="No similar past cases found",
                conclusion="Cannot apply analogical reasoning",
                confidence=0.0,
                supporting_evidence=[{"factors": factors, "cases_analyzed": 0}]
            )
        
        success_count = 0
        failure_count = 0
        avg_similarity = 0
        
        for case in similar_cases:
            similarity = case.get("similarity", 0.5)
            outcome = case.get("outcome", {}).get("success", None)
            
            avg_similarity += similarity
            
            if outcome is True:
                success_count += similarity
                evidence.append({
                    "case_id": case.get("id"),
                    "similarity": similarity,
                    "outcome": "success",
                    "notes": case.get("outcome", {}).get("notes", "")
                })
            elif outcome is False:
                failure_count += similarity
                evidence.append({
                    "case_id": case.get("id"),
                    "similarity": similarity,
                    "outcome": "failure",
                    "notes": case.get("outcome", {}).get("notes", "")
                })
        
        avg_similarity /= max(len(similar_cases), 1)
        total_weighted = success_count + failure_count
        
        if total_weighted > 0:
            success_rate_from_analogy = success_count / total_weighted
            factors["success_rate_from_similar"] = success_rate_from_analogy
        else:
            success_rate_from_analogy = 0.5
        
        factors["analogy_confidence"] = avg_similarity
        
        conclusion = f"Similar cases: {success_count:.1f} successes vs {failure_count:.1f} failures"
        
        return ReasoningStep(
            step_number=2,
            pramana=PramanaType.UPAMANA,
            premise="Comparison with similar past cases",
            conclusion=conclusion,
            confidence=avg_similarity,
            supporting_evidence=[{
                "factors": factors,
                "cases_analyzed": len(similar_cases),
                "success_count": success_count,
                "failure_count": failure_count,
                "case_outcomes": evidence
            }]
        )

    def _anumana_inference(
        self,
        aggregated_factors: Dict,
        task_features: Dict
    ) -> ReasoningStep:
        """
        ANUMANA: Logical inference from patterns.
        
        Apply inference rules:
        - High complexity + long deadline → increased risk
        - Team required + good past coordination → positive factor
        - Time pressure reduces success probability
        """
        logger.debug("[Anumana] Applying logical inference")
        
        factors = {}
        evidence = []
        
        # Inference rule 1: Complexity × Urgency
        complexity = aggregated_factors.get("complexity", 0.5)
        urgency = aggregated_factors.get("deadline_urgency", 0.2)
        time_risk = complexity * urgency
        
        factors["time_risk_inference"] = time_risk
        evidence.append({
            "rule": "high_complexity_with_urgency_increases_risk",
            "formula": f"complexity({complexity:.2f}) * urgency({urgency:.2f}) = {time_risk:.2f}",
            "applies": time_risk > 0.3
        })
        
        # Inference rule 2: Team coordination overhead
        if aggregated_factors.get("team_required"):
            factors["team_coordination_risk"] = 0.15  # Team adds 15% risk baseline
            evidence.append({
                "rule": "team_coordination_adds_risk",
                "base_risk": 0.15,
                "applies": True
            })
        
        # Inference rule 3: Estimation accuracy
        estimated_effort = aggregated_factors.get("estimated_effort_hours", 10)
        if estimated_effort > 40:
            # Long tasks have higher estimation error
            factors["estimation_uncertainty"] = 0.2
            evidence.append({
                "rule": "long_tasks_have_high_uncertainty",
                "hours": estimated_effort,
                "uncertainty_penalty": 0.2
            })
        
        # Aggregate inference
        inference_score = (
            time_risk * 0.4 +
            factors.get("team_coordination_risk", 0) * 0.3 +
            factors.get("estimation_uncertainty", 0) * 0.3
        )
        
        factors["aggregated_inference_risk"] = inference_score
        
        return ReasoningStep(
            step_number=3,
            pramana=PramanaType.ANUMANA,
            premise="Logical inference from task patterns",
            conclusion=f"Inferred risk score: {inference_score:.2f}",
            confidence=0.85,
            supporting_evidence=[{"factors": factors, "inference_rules": evidence}]
        )

    def _sabda_analysis(
        self,
        task_features: Dict,
        similar_cases: List[Dict]
    ) -> ReasoningStep:
        """
        SABDA: Application of authority (historical best practices).
        
        Rules:
        - Similar tasks done by experienced team → +20% success boost
        - Tasks with documented process → +15% success boost
        - First-time task type → -15% success penalty
        """
        logger.debug("[Sabda] Applying historical best practices")
        
        factors = {}
        evidence = []
        
        # Authority factor 1: Experience level
        if similar_cases:
            avg_team_experience = 0
            for case in similar_cases[:3]:
                team_exp = case.get("team_average_experience_years", 2)
                avg_team_experience += team_exp
            
            if similar_cases:
                avg_team_experience /= min(len(similar_cases), 3)
                
                if avg_team_experience >= 5:
                    factors["experience_boost"] = 0.2
                    evidence.append({
                        "authority_rule": "experienced_team",
                        "avg_years": avg_team_experience,
                        "boost": 0.2
                    })
                elif avg_team_experience >= 2:
                    factors["experience_boost"] = 0.1
                    evidence.append({
                        "authority_rule": "moderate_experience",
                        "avg_years": avg_team_experience,
                        "boost": 0.1
                    })
        
        # Authority factor 2: Documented process
        if task_features.get("has_documented_process"):
            factors["process_documentation_boost"] = 0.15
            evidence.append({
                "authority_rule": "documented_process_available",
                "boost": 0.15
            })
        
        # Authority factor 3: First-time vs repetition
        if task_features.get("task_type_first_time"):
            factors["first_time_penalty"] = -0.15
            evidence.append({
                "authority_rule": "first_time_task_type",
                "penalty": -0.15
            })
        
        sabda_score = sum(v for k, v in factors.items() if "boost" in k or "penalty" in k)
        
        return ReasoningStep(
            step_number=4,
            pramana=PramanaType.SABDA,
            premise="Historical best practices and authority",
            conclusion=f"Best practices adjustment: {sabda_score:+.2f}",
            confidence=0.80,
            supporting_evidence=[{"factors": factors, "authority_rules": evidence}]
        )

    def _aggregate_predictions(
        self,
        reasoning_chain: List[ReasoningStep]
    ) -> Tuple[float, float]:
        """
        Aggregate predictions from all reasoning steps.
        
        Returns:
            (final_prediction, confidence_score)
        """
        predictions = []
        confidences = []
        
        for step in reasoning_chain:
            # Extract prediction from step's supporting evidence
            factors = step.supporting_evidence[0].get("factors", {})
            
            # Convert factors to prediction
            if step.pramana == PramanaType.PRATYAKSHA:
                # Direct observation: predict based on complexity inverse
                pred = 1.0 - factors.get("complexity", 0.5)
            elif step.pramana == PramanaType.UPAMANA:
                # Analogy: use success rate from similar cases
                pred = factors.get("success_rate_from_similar", 0.5)
            elif step.pramana == PramanaType.ANUMANA:
                # Inference: use inverse of inferred risk
                pred = 1.0 - factors.get("aggregated_inference_risk", 0.5)
            elif step.pramana == PramanaType.SABDA:
                # Authority: apply boost/penalty
                pred = 0.5 + sum(v for v in factors.values() if isinstance(v, (int, float)))
            else:
                pred = 0.5
            
            pred = min(max(pred, 0.0), 1.0)  # Clamp to [0, 1]
            predictions.append(pred)
            confidences.append(step.confidence)
        
        # Weighted average: confidence-weighted prediction
        if confidences:
            final_prediction = sum(p * c for p, c in zip(predictions, confidences)) / sum(confidences)
        else:
            final_prediction = 0.5
        
        # Confidence: average of all confidences
        confidence_score = sum(confidences) / len(confidences) if confidences else 0.5
        
        return min(max(final_prediction, 0.0), 1.0), confidence_score

    def _generate_recommendations(
        self,
        factors: Dict,
        prediction: float
    ) -> List[str]:
        """Generate actionable recommendations based on reasoning."""
        recommendations = []
        
        if prediction > 0.8:
            recommendations.append("✓ High success probability. Recommend proceeding.")
        elif prediction > 0.6:
            recommendations.append("✓ Moderate success probability. Proceed with caution and risk mitigations.")
        else:
            recommendations.append("⚠️  Low success probability. Consider breaking into smaller tasks or re-scoping.")
        
        if factors.get("time_risk_inference", 0) > 0.3:
            recommendations.append("📅 High time-risk detected: Add buffer to schedule or reduce scope.")
        
        if factors.get("team_coordination_risk", 0) > 0.1:
            recommendations.append("👥 Team coordination required: Establish clear communication plan.")
        
        if factors.get("estimation_uncertainty", 0) > 0.15:
            recommendations.append("📊 High estimation uncertainty: Set up milestone checkpoints.")
        
        return recommendations

    def _store_reasoning_trace(self, trace: ReasoningTrace, user_id: Optional[str]):
        """Store reasoning trace for audit and learning."""
        try:
            doc = {
                "task_id": trace.task_id,
                "task_description": trace.task_description,
                "reasoning_chain": [
                    {
                        "step_number": s.step_number,
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
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
            }
            self.reasoning_collection.insert_one(doc)
            logger.info(f"[NyayaEngine] Reasoning trace stored for task {trace.task_id}")
        except Exception as e:
            logger.error(f"[NyayaEngine] Error storing reasoning trace: {e}")


# Singleton instance
_nyaya_engine = None


def get_nyaya_reasoning_engine(db=None, search_service=None) -> NyayaReasoningEngine:
    """Get or create singleton NyayaReasoningEngine instance."""
    global _nyaya_engine
    if _nyaya_engine is None:
        _nyaya_engine = NyayaReasoningEngine(db=db, search_service=search_service)
    return _nyaya_engine
