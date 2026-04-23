"""
TRUTH AGENT — Verification & Claim Validation
Implements RAG-based verification, risk scoring, and execution blocking.
"""

import logging
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json

from services.mongodb_service import get_db
from services.hybrid_search_service import get_hybrid_search_service

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk severity classification."""
    CRITICAL = "critical"      # Risk > 0.8 → block
    HIGH = "high"              # Risk > 0.6 → require approval
    MEDIUM = "medium"          # Risk > 0.4 → warn
    LOW = "low"                # Risk <= 0.4 → proceed
    NONE = "none"              # Risk == 0


@dataclass
class VerificationResult:
    """Result of claim verification."""
    claim: str
    is_verified: bool
    risk_score: float  # [0, 1] where 1 = highest risk
    confidence_score: float  # [0, 1] where 1 = most confident
    risk_level: RiskLevel
    evidence: List[Dict]  # Retrieved similar cases / past outcomes
    reasoning: str  # Explanation of verdict
    mitigations: List[str]  # Suggested risk mitigations
    blocking_reason: Optional[str]  # Why execution should be blocked
    timestamp: str


class TrustAgent:
    """
    Verification agent that validates claims before execution.
    
    Implements:
    - RAG-based verification (retrieve similar cases)
    - Risk scoring based on historical outcomes
    - Confidence scoring based on evidence strength
    - Automatic blocking for high-risk operations
    """

    def __init__(self, db=None, search_service=None):
        self.db = db or get_db()
        self.search_service = search_service or get_hybrid_search_service()
        self.verification_collection = self.db["verifications"]
        self.risk_collection = self.db["risk_assessments"]
        
        # Ensure indexes
        self.verification_collection.create_index("timestamp")
        self.verification_collection.create_index("is_verified")
        self.risk_collection.create_index("risk_level")

    def verify_claim(
        self,
        claim: str,
        context: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a claim using RAG + historical context.
        
        Args:
            claim: The statement to verify (e.g., "Task will complete in 2 hours")
            context: Additional context (task_id, dependencies, etc.)
            user_id: User who made the claim
            
        Returns:
            VerificationResult with risk scores and mitigations
        """
        logger.info(f"[TrustAgent] Verifying claim: {claim}")
        
        # Step 1: Retrieve similar past cases (RAG)
        similar_cases = self._retrieve_similar_cases(claim, context)
        
        # Step 2: Extract claim components
        claim_factors = self._extract_claim_factors(claim, context)
        
        # Step 3: Compute risk score from historical outcomes
        risk_score, evidence = self._compute_risk_score(claim_factors, similar_cases)
        
        # Step 4: Compute confidence from evidence strength
        confidence_score = self._compute_confidence(evidence, similar_cases)
        
        # Step 5: Determine risk level
        risk_level = self._get_risk_level(risk_score)
        
        # Step 6: Generate reasoning & mitigations
        reasoning = self._generate_reasoning(claim, evidence, risk_level)
        mitigations = self._suggest_mitigations(claim_factors, risk_level)
        
        # Step 7: Determine if claim is verified
        is_verified = risk_score <= 0.6 and confidence_score >= 0.5
        
        # Step 8: Blocking decision
        blocking_reason = None
        if risk_score > 0.8:
            blocking_reason = f"Critical risk ({risk_score:.2f}). Operation blocked."
        
        result = VerificationResult(
            claim=claim,
            is_verified=is_verified,
            risk_score=risk_score,
            confidence_score=confidence_score,
            risk_level=risk_level,
            evidence=evidence,
            reasoning=reasoning,
            mitigations=mitigations,
            blocking_reason=blocking_reason,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store verification in database
        self._store_verification(result, user_id, context)
        
        return result

    def _retrieve_similar_cases(
        self,
        claim: str,
        context: Optional[Dict] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve similar past cases using hybrid search.
        """
        try:
            search_query = claim
            if context and "task_type" in context:
                search_query += f" {context['task_type']}"
            
            results = self.search_service.hybrid_search(
                query=search_query,
                user_id=context.get("user_id") if context else None,
                top_k=top_k
            )
            
            logger.info(f"[TrustAgent] Retrieved {len(results)} similar cases")
            return results
        except Exception as e:
            logger.error(f"[TrustAgent] Error retrieving similar cases: {e}")
            return []

    def _extract_claim_factors(self, claim: str, context: Optional[Dict]) -> Dict:
        """
        Extract key factors from the claim for risk assessment.
        
        Examples:
        - "Task will complete in 2 hours" → {"estimated_duration": 2, "unit": "hours"}
        - "Team has 5 resources" → {"team_size": 5}
        - "High priority task" → {"priority": "high"}
        """
        factors = {}
        
        # Try to extract temporal factors
        if "hour" in claim.lower():
            try:
                import re
                match = re.search(r'(\d+)\s*hours?', claim, re.IGNORECASE)
                if match:
                    factors["estimated_duration_hours"] = int(match.group(1))
            except:
                pass
        
        if "day" in claim.lower():
            try:
                import re
                match = re.search(r'(\d+)\s*days?', claim, re.IGNORECASE)
                if match:
                    factors["estimated_duration_days"] = int(match.group(1))
            except:
                pass
        
        # Priority markers
        if any(x in claim.lower() for x in ["high priority", "urgent", "critical"]):
            factors["priority"] = "high"
        elif any(x in claim.lower() for x in ["low priority", "backlog"]):
            factors["priority"] = "low"
        
        # Resource markers
        if "team" in claim.lower() or "resource" in claim.lower():
            factors["has_team_dependency"] = True
        
        # Add context factors
        if context:
            factors.update(context)
        
        return factors

    def _compute_risk_score(
        self,
        claim_factors: Dict,
        similar_cases: List[Dict]
    ) -> Tuple[float, List[Dict]]:
        """
        Compute risk score based on historical outcomes.
        
        Logic:
        - If similar cases succeeded → lower risk
        - If similar cases failed → higher risk
        - If no cases found → moderate risk (confidence penalty)
        """
        if not similar_cases:
            # No evidence → moderate risk
            base_risk = 0.5
            evidence = [{"type": "no_similar_cases", "weight": 0}]
            return base_risk, evidence
        
        evidence = []
        success_count = 0
        failure_count = 0
        
        for case in similar_cases:
            outcome = case.get("outcome", {}).get("success", None)
            if outcome is True:
                success_count += 1
                evidence.append({
                    "type": "similar_success",
                    "case_id": case.get("id"),
                    "similarity": case.get("similarity", 0),
                    "weight": 1.0
                })
            elif outcome is False:
                failure_count += 1
                evidence.append({
                    "type": "similar_failure",
                    "case_id": case.get("id"),
                    "similarity": case.get("similarity", 0),
                    "weight": -1.0
                })
        
        total_cases = success_count + failure_count
        if total_cases > 0:
            failure_rate = failure_count / total_cases
            # Risk = failure rate, capped at [0, 1]
            risk_score = min(max(failure_rate, 0.0), 1.0)
        else:
            risk_score = 0.5
        
        # Adjust for claim factors
        if claim_factors.get("estimated_duration_days", 0) > 30:
            risk_score += 0.1  # Long-duration tasks have higher inherent risk
        if claim_factors.get("has_team_dependency"):
            risk_score += 0.05  # Team dependencies add risk
        if claim_factors.get("priority") == "high":
            risk_score += 0.05  # High-pressure situations increase risk
        
        # Cap at [0, 1]
        risk_score = min(max(risk_score, 0.0), 1.0)
        
        return risk_score, evidence

    def _compute_confidence(self, evidence: List[Dict], similar_cases: List[Dict]) -> float:
        """
        Compute confidence in verification based on evidence strength.
        
        Factors:
        - Number of similar cases (more = higher confidence)
        - Case similarity scores (higher = higher confidence)
        - Evidence variety (more types = higher confidence)
        """
        if not evidence:
            return 0.0
        
        # Base: number of similar cases
        num_cases = len(similar_cases)
        case_confidence = min(num_cases / 10, 1.0)  # Max 10 cases for full confidence
        
        # Similarity score: average of similarity weights
        avg_similarity = 0
        if similar_cases:
            avg_similarity = sum(c.get("similarity", 0) for c in similar_cases) / len(similar_cases)
        
        similarity_confidence = avg_similarity  # Already [0, 1]
        
        # Evidence variety
        evidence_types = len(set(e.get("type") for e in evidence))
        variety_confidence = min(evidence_types / 3, 1.0)  # Max 3 types for full confidence
        
        # Weighted average
        confidence = (
            0.5 * case_confidence +
            0.3 * similarity_confidence +
            0.2 * variety_confidence
        )
        
        return min(max(confidence, 0.0), 1.0)

    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        """Map risk score to risk level."""
        if risk_score > 0.8:
            return RiskLevel.CRITICAL
        elif risk_score > 0.6:
            return RiskLevel.HIGH
        elif risk_score > 0.4:
            return RiskLevel.MEDIUM
        elif risk_score > 0:
            return RiskLevel.LOW
        else:
            return RiskLevel.NONE

    def _generate_reasoning(
        self,
        claim: str,
        evidence: List[Dict],
        risk_level: RiskLevel
    ) -> str:
        """
        Generate human-readable reasoning for verification verdict.
        """
        success_count = sum(1 for e in evidence if e.get("type") == "similar_success")
        failure_count = sum(1 for e in evidence if e.get("type") == "similar_failure")
        
        reasoning_parts = [
            f"Verifying claim: '{claim}'",
            f"Historical data: {success_count} successes, {failure_count} failures",
        ]
        
        if risk_level == RiskLevel.CRITICAL:
            reasoning_parts.append("⚠️  CRITICAL RISK: Historical similar cases mostly failed.")
        elif risk_level == RiskLevel.HIGH:
            reasoning_parts.append("⚠️  HIGH RISK: Multiple similar failures detected.")
        elif risk_level == RiskLevel.MEDIUM:
            reasoning_parts.append("⚠️  MEDIUM RISK: Some uncertainty in historical outcomes.")
        elif risk_level == RiskLevel.LOW:
            reasoning_parts.append("✓ LOW RISK: Similar cases mostly succeeded.")
        else:
            reasoning_parts.append("✓ NO RISK: Claim appears safe based on evidence.")
        
        return "\n".join(reasoning_parts)

    def _suggest_mitigations(self, claim_factors: Dict, risk_level: RiskLevel) -> List[str]:
        """
        Suggest risk mitigation strategies.
        """
        mitigations = []
        
        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            mitigations.append("Break task into smaller subtasks for better control")
            mitigations.append("Allocate buffer time (add 50% to estimate)")
            mitigations.append("Increase team oversight and check-ins")
        
        if claim_factors.get("estimated_duration_days", 0) > 30:
            mitigations.append("Long-duration task: establish milestone checkpoints every 5 days")
        
        if claim_factors.get("has_team_dependency"):
            mitigations.append("Team dependency detected: confirm resource availability upfront")
        
        if claim_factors.get("priority") == "high":
            mitigations.append("High priority: assign backup resources")
        
        return mitigations

    def _store_verification(
        self,
        result: VerificationResult,
        user_id: Optional[str],
        context: Optional[Dict]
    ):
        """Store verification result in database for audit."""
        try:
            doc = {
                "claim": result.claim,
                "is_verified": result.is_verified,
                "risk_score": result.risk_score,
                "confidence_score": result.confidence_score,
                "risk_level": result.risk_level.value,
                "evidence_count": len(result.evidence),
                "blocking_reason": result.blocking_reason,
                "user_id": user_id,
                "context": context,
                "timestamp": datetime.utcnow(),
            }
            self.verification_collection.insert_one(doc)
            logger.info(f"[TrustAgent] Verification stored: {result.risk_level}")
        except Exception as e:
            logger.error(f"[TrustAgent] Error storing verification: {e}")

    def should_block_execution(self, verification_result: VerificationResult) -> bool:
        """
        Determine if execution should be blocked.
        
        Blocking rules:
        - Risk > 0.8 → block
        - Risk > 0.6 AND confidence < 0.5 → block
        """
        if verification_result.risk_score > 0.8:
            return True
        if verification_result.risk_score > 0.6 and verification_result.confidence_score < 0.5:
            return True
        return False

    def get_verification_stats(self) -> Dict:
        """Get summary statistics on verifications."""
        try:
            total = self.verification_collection.count_documents({})
            verified = self.verification_collection.count_documents({"is_verified": True})
            blocked = self.verification_collection.count_documents({"blocking_reason": {"$ne": None}})
            
            return {
                "total_verifications": total,
                "verified": verified,
                "blocked": blocked,
                "verification_rate": verified / total if total > 0 else 0,
                "block_rate": blocked / total if total > 0 else 0,
            }
        except Exception as e:
            logger.error(f"[TrustAgent] Error getting verification stats: {e}")
            return {}


# Singleton instance
_trust_agent = None


def get_trust_agent(db=None, search_service=None) -> TrustAgent:
    """Get or create singleton TrustAgent instance."""
    global _trust_agent
    if _trust_agent is None:
        _trust_agent = TrustAgent(db=db, search_service=search_service)
    return _trust_agent
