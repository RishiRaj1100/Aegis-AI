"""
BIAS & FAIRNESS DETECTION SERVICE — Algorithmic Fairness Analysis

Purpose: Monitor for demographic disparities and ensure fair AI decision-making
Tracks accuracy gaps by demographic groups and alerts on fairness violations
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging
from statistics import mean, stdev
from math import sqrt

from services.mongodb_service import get_db

logger = logging.getLogger(__name__)


class FairnessMetric(str, Enum):
    """Fairness metrics."""
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUALIZED_ODDS = "equalized_odds"
    CALIBRATION = "calibration"
    ACCURACY_GAP = "accuracy_gap"
    PREDICTIVE_PARITY = "predictive_parity"


@dataclass
class GroupAccuracy:
    """Accuracy metrics for a demographic group."""
    group_name: str
    group_size: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    positive_rate: float  # % of positive predictions


@dataclass
class FairnessAlert:
    """Alert when fairness threshold is violated."""
    timestamp: datetime
    metric_type: FairnessMetric
    group_a: str
    group_b: str
    difference: float  # Gap in metric value
    threshold: float  # Fairness threshold
    is_violation: bool
    recommendation: str


@dataclass
class BiasAnalysisResult:
    """Complete bias and fairness analysis."""
    analysis_date: datetime
    demographic_attribute: str  # e.g., "user_department", "experience_level"
    groups: Dict[str, GroupAccuracy]
    max_accuracy_gap: float
    max_accuracy_gap_groups: Tuple[str, str]
    
    accuracy_gap_is_fair: bool
    demographic_parity_gap: float
    demographic_parity_is_fair: bool
    
    alerts: List[FairnessAlert]
    
    feature_importances: Optional[Dict[str, float]]  # Via SHAP


class BiasDetectionService:
    """Detects algorithmic bias and fairness issues."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db = get_db()
        self._setup_collections()
        
        # Fairness thresholds (configurable)
        self.accuracy_gap_threshold = 0.10  # 10% accuracy difference
        self.demographic_parity_threshold = 0.20  # 20% difference in approval rates
        
        self._initialized = True
        logger.info("[BiasDetection] Service initialized")
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        fairness = self.db["fairness_analysis"]
        fairness.create_index([("created_at", -1)])
        fairness.create_index([("demographic_attribute", 1)])
        
        fairness_alerts = self.db["fairness_alerts"]
        fairness_alerts.create_index([("timestamp", -1)])
        fairness_alerts.create_index([("is_violation", 1)])
    
    def record_prediction_for_fairness(self, task_id: str, user_id: str,
                                       predicted_success: bool,
                                       actual_success: bool,
                                       demographics: Dict[str, str]) -> Dict:
        """
        Record prediction with demographic information for fairness tracking.
        
        Args:
            task_id: Task identifier
            user_id: User identifier
            predicted_success: Prediction (True/False)
            actual_success: Actual outcome (True/False)
            demographics: Dict like {"department": "engineering", "experience": "senior"}
        """
        try:
            record = {
                "task_id": task_id,
                "user_id": user_id,
                "predicted_success": predicted_success,
                "actual_success": actual_success,
                "correct": predicted_success == actual_success,
                "demographics": demographics,
                "timestamp": datetime.utcnow(),
            }
            
            self.db["prediction_demographics"].insert_one(record)
            logger.debug(f"[BiasDetection] Recorded prediction: {task_id}")
            
            return {"recorded": True}
        
        except Exception as e:
            logger.error(f"[BiasDetection] Error recording prediction: {e}")
            raise
    
    def compute_group_metrics(self, demographic_attribute: str,
                             group_value: str,
                             window_days: int = 30) -> GroupAccuracy:
        """
        Compute accuracy metrics for a specific demographic group.
        
        Args:
            demographic_attribute: e.g., "department", "experience_level"
            group_value: e.g., "engineering", "senior"
            window_days: Days of data to analyze
        
        Returns:
            GroupAccuracy with metrics for the group
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=window_days)
            
            # Query predictions for this demographic group
            predictions = list(self.db["prediction_demographics"].find({
                f"demographics.{demographic_attribute}": group_value,
                "timestamp": {"$gte": cutoff_date}
            }))
            
            if not predictions:
                logger.warning(f"[BiasDetection] No data for {demographic_attribute}={group_value}")
                return GroupAccuracy(
                    group_name=group_value, group_size=0,
                    accuracy=0.0, precision=0.0, recall=0.0, f1_score=0.0,
                    positive_rate=0.0
                )
            
            # Confusion matrix
            tp = sum(1 for p in predictions
                    if p["correct"] and p["actual_success"])
            tn = sum(1 for p in predictions
                    if p["correct"] and not p["actual_success"])
            fp = sum(1 for p in predictions
                    if not p["correct"] and p["predicted_success"])
            fn = sum(1 for p in predictions
                    if not p["correct"] and not p["predicted_success"])
            
            # Metrics
            n = len(predictions)
            accuracy = (tp + tn) / n if n > 0 else 0.0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            positive_rate = sum(1 for p in predictions if p["predicted_success"]) / n
            
            return GroupAccuracy(
                group_name=group_value,
                group_size=n,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                positive_rate=positive_rate
            )
        
        except Exception as e:
            logger.error(f"[BiasDetection] Error computing group metrics: {e}")
            raise
    
    def analyze_demographic_parity(self, demographic_attribute: str,
                                  window_days: int = 30) -> BiasAnalysisResult:
        """
        Analyze demographic parity and accuracy gaps by demographic attribute.
        
        Args:
            demographic_attribute: e.g., "department", "experience_level", "region"
            window_days: Days of data to analyze
        
        Returns:
            BiasAnalysisResult with comprehensive fairness analysis
        """
        try:
            logger.info(f"[BiasDetection] Analyzing demographic parity for {demographic_attribute}")
            
            cutoff_date = datetime.utcnow() - timedelta(days=window_days)
            
            # Get all unique groups
            groups_data = list(self.db["prediction_demographics"].aggregate([
                {"$match": {
                    f"demographics.{demographic_attribute}": {"$exists": True},
                    "timestamp": {"$gte": cutoff_date}
                }},
                {"$group": {f"_id": f"$demographics.{demographic_attribute}"}},
            ]))
            
            if not groups_data:
                logger.warning(f"[BiasDetection] No groups found for {demographic_attribute}")
                return BiasAnalysisResult(
                    analysis_date=datetime.utcnow(),
                    demographic_attribute=demographic_attribute,
                    groups={},
                    max_accuracy_gap=0.0,
                    max_accuracy_gap_groups=("", ""),
                    accuracy_gap_is_fair=True,
                    demographic_parity_gap=0.0,
                    demographic_parity_is_fair=True,
                    alerts=[],
                    feature_importances=None
                )
            
            # Compute metrics for each group
            group_names = [g["_id"] for g in groups_data]
            group_metrics = {}
            
            for group_name in group_names:
                metrics = self.compute_group_metrics(demographic_attribute, group_name, window_days)
                group_metrics[group_name] = metrics
            
            # Compute accuracy gaps
            accuracies = {name: m.accuracy for name, m in group_metrics.items()}
            max_acc = max(accuracies.values()) if accuracies else 0.0
            min_acc = min(accuracies.values()) if accuracies else 0.0
            max_accuracy_gap = max_acc - min_acc
            
            # Find groups with max gap
            max_group = max(group_metrics.items(), key=lambda x: x[1].accuracy)[0] if group_metrics else ""
            min_group = min(group_metrics.items(), key=lambda x: x[1].accuracy)[0] if group_metrics else ""
            
            # Demographic parity (difference in positive prediction rates)
            positive_rates = {name: m.positive_rate for name, m in group_metrics.items()}
            max_parity = max(positive_rates.values()) - min(positive_rates.values()) if positive_rates else 0.0
            
            # Fairness checks
            accuracy_is_fair = max_accuracy_gap <= self.accuracy_gap_threshold
            parity_is_fair = max_parity <= self.demographic_parity_threshold
            
            # Generate alerts
            alerts = []
            if not accuracy_is_fair:
                alert = FairnessAlert(
                    timestamp=datetime.utcnow(),
                    metric_type=FairnessMetric.ACCURACY_GAP,
                    group_a=max_group,
                    group_b=min_group,
                    difference=max_accuracy_gap,
                    threshold=self.accuracy_gap_threshold,
                    is_violation=True,
                    recommendation=f"Accuracy gap of {max_accuracy_gap:.1%} between {max_group} and {min_group} exceeds threshold of {self.accuracy_gap_threshold:.1%}. "
                                  f"Review model predictions for these groups and consider group-specific retraining."
                )
                alerts.append(alert)
                self.db["fairness_alerts"].insert_one({
                    "timestamp": alert.timestamp,
                    "metric_type": alert.metric_type.value,
                    "is_violation": alert.is_violation,
                    "recommendation": alert.recommendation,
                })
            
            if not parity_is_fair:
                alert = FairnessAlert(
                    timestamp=datetime.utcnow(),
                    metric_type=FairnessMetric.DEMOGRAPHIC_PARITY,
                    group_a=max(group_metrics.items(), key=lambda x: x[1].positive_rate)[0],
                    group_b=min(group_metrics.items(), key=lambda x: x[1].positive_rate)[0],
                    difference=max_parity,
                    threshold=self.demographic_parity_threshold,
                    is_violation=True,
                    recommendation=f"Approval rate disparity of {max_parity:.1%} between groups exceeds threshold of {self.demographic_parity_threshold:.1%}. "
                                  f"This may indicate disparate impact. Review selection criteria."
                )
                alerts.append(alert)
                self.db["fairness_alerts"].insert_one({
                    "timestamp": alert.timestamp,
                    "metric_type": alert.metric_type.value,
                    "is_violation": alert.is_violation,
                    "recommendation": alert.recommendation,
                })
            
            # Feature importances (placeholder - would use SHAP)
            feature_importances = self._compute_feature_importances()
            
            result = BiasAnalysisResult(
                analysis_date=datetime.utcnow(),
                demographic_attribute=demographic_attribute,
                groups=group_metrics,
                max_accuracy_gap=max_accuracy_gap,
                max_accuracy_gap_groups=(max_group, min_group),
                accuracy_gap_is_fair=accuracy_is_fair,
                demographic_parity_gap=max_parity,
                demographic_parity_is_fair=parity_is_fair,
                alerts=alerts,
                feature_importances=feature_importances
            )
            
            logger.info(f"[BiasDetection] Analysis complete. Accuracy gap: {max_accuracy_gap:.1%}, "
                       f"Parity gap: {max_parity:.1%}")
            
            return result
        
        except Exception as e:
            logger.error(f"[BiasDetection] Error analyzing demographic parity: {e}")
            raise
    
    def _compute_feature_importances(self) -> Dict[str, float]:
        """
        Compute feature importances using SHAP on the Catalyst model.
        """
        try:
            import os
            import joblib
            import pandas as pd
            from services.explainability import ExplainabilityService
            
            model_path = os.path.join("models", "pretrained", "catalyst_success_predictor.pkl")
            if not os.path.exists(model_path):
                logger.warning("[BiasDetection] Catalyst model not found.")
                return {}
                
            model = joblib.load(model_path)
            
            # Baseline feature set to evaluate SHAP
            features = pd.DataFrame([{
                "goal_length_words": 20, "num_subtasks": 5, "clarity": 0.6,
                "info_quality": 0.6, "feasibility": 0.6, "manageability": 0.6,
                "resource_adequacy": 0.6, "uncertainty": 0.4, "past_success_rate": 0.6,
                "similarity_score": 0.5, "case_signal": 0.5, "context_signal": 0.5,
                "trust_signal": 0.6, "reflection_signal": 0.5,
            }])
            
            if hasattr(model, "feature_names_in_"):
                # Align columns with model
                cols = list(model.feature_names_in_)
                for c in cols:
                    if c not in features.columns:
                        features[c] = 0.5
                features = features[cols]
                
            explainer = ExplainabilityService()
            shap_map, _, _ = explainer.explain_prediction(model, features, top_k=5)
            
            if not shap_map and hasattr(model, "feature_importances_"):
                # Fallback to global feature importances if SHAP is missing
                importances = model.feature_importances_
                cols = list(model.feature_names_in_) if hasattr(model, "feature_names_in_") else list(features.columns)
                shap_map = {name: float(imp) for name, imp in zip(cols, importances)}
                
            # Take absolute values and normalize to percentages
            abs_map = {k: abs(v) for k, v in shap_map.items()}
            total = sum(abs_map.values())
            if total > 0:
                abs_map = {k: v / total for k, v in abs_map.items()}
                
            ranked = sorted(abs_map.items(), key=lambda x: x[1], reverse=True)[:5]
            return dict(ranked)
            
        except Exception as e:
            logger.error(f"[BiasDetection] Error computing feature importances: {e}")
            return {}
    
    def get_fairness_dashboard(self) -> Dict:
        """Get comprehensive fairness dashboard summary."""
        try:
            # Analyze key demographic attributes
            demographic_attributes = ["department", "experience_level", "region"]
            
            analyses = {}
            total_violations = 0
            
            for attr in demographic_attributes:
                result = self.analyze_demographic_parity(attr, window_days=30)
                analyses[attr] = {
                    "max_accuracy_gap": result.max_accuracy_gap,
                    "accuracy_fair": result.accuracy_gap_is_fair,
                    "demographic_parity_gap": result.demographic_parity_gap,
                    "parity_fair": result.demographic_parity_is_fair,
                    "alerts_count": len(result.alerts),
                }
                total_violations += len(result.alerts)
            
            # Get recent alerts
            recent_alerts = list(self.db["fairness_alerts"].find(
                {"is_violation": True}
            ).sort("timestamp", -1).limit(10))
            
            fairness_score = 100.0
            for attr_result in analyses.values():
                if not attr_result["accuracy_fair"]:
                    fairness_score -= 20
                if not attr_result["parity_fair"]:
                    fairness_score -= 20
            
            fairness_score = max(0, fairness_score)
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "fairness_score": f"{fairness_score:.0f}/100",
                "total_violations": total_violations,
                "analyses": analyses,
                "recent_alerts": [
                    {
                        "timestamp": alert["timestamp"].isoformat(),
                        "metric_type": alert["metric_type"],
                        "recommendation": alert["recommendation"],
                    }
                    for alert in recent_alerts
                ],
            }
        
        except Exception as e:
            logger.error(f"[BiasDetection] Error generating fairness dashboard: {e}")
            raise


# Singleton accessor
def get_bias_detection_service() -> BiasDetectionService:
    """Get or create the BiasDetectionService singleton."""
    return BiasDetectionService()
