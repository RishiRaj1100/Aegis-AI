"""
A/B TESTING SERVICE — Randomized Experiment Framework

Purpose: Run controlled experiments to validate AI prioritization impact
Compares Group A (no AI) vs Group B (with AI) on business metrics
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import hashlib
from statistics import mean, stdev
from math import sqrt

from services.mongodb_service import get_db

logger = logging.getLogger(__name__)


class ExperimentGroup:
    """A/B test groups."""
    CONTROL = "A"  # No AI prioritization
    TREATMENT = "B"  # AI prioritization enabled


@dataclass
class ExperimentResult:
    """A/B test statistical result."""
    experiment_id: str
    group_a_mean: float
    group_b_mean: float
    group_a_count: int
    group_b_count: int
    
    t_statistic: float
    p_value: float
    is_significant: bool  # p_value < 0.05
    
    effect_size: float  # Cohen's d
    confidence_interval: Tuple[float, float]  # 95% CI
    
    winner: Optional[str]  # "A", "B", or None if not significant
    recommendation: str


class ABTestService:
    """A/B testing service for controlled experiments."""
    
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
        self._initialized = True
        logger.info("[ABTest] Service initialized")
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        experiments = self.db["ab_experiments"]
        experiments.create_index([("experiment_id", 1)])
        experiments.create_index([("created_at", -1)])
        experiments.create_index([("status", 1)])
        
        experiment_data = self.db["ab_experiment_data"]
        experiment_data.create_index([("experiment_id", 1), ("user_id", 1)])
        experiment_data.create_index([("experiment_id", 1), ("group", 1)])
        experiment_data.create_index([("timestamp", -1)])
    
    def assign_group(self, user_id: str, experiment_id: str = "prioritization_v1") -> str:
        """
        Deterministically assign user to group A or B.
        
        Uses hash-based assignment for reproducibility:
        - Group A (Control): 50% of users (no AI prioritization)
        - Group B (Treatment): 50% of users (with AI prioritization)
        
        Args:
            user_id: User identifier
            experiment_id: Experiment name
        
        Returns:
            "A" or "B"
        """
        try:
            # Deterministic assignment based on hash
            hash_obj = hashlib.md5(f"{experiment_id}:{user_id}".encode())
            hash_val = int(hash_obj.hexdigest(), 16)
            
            group = ExperimentGroup.CONTROL if (hash_val % 2) == 0 else ExperimentGroup.TREATMENT
            
            logger.debug(f"[ABTest] Assigned {user_id} to group {group}")
            return group
        
        except Exception as e:
            logger.error(f"[ABTest] Error assigning group: {e}")
            return ExperimentGroup.CONTROL
    
    def create_experiment(self, experiment_id: str, name: str,
                         hypothesis: str, start_date: str,
                         end_date: str, metrics: List[str]) -> Dict:
        """Create a new A/B test experiment."""
        try:
            experiment = {
                "experiment_id": experiment_id,
                "name": name,
                "hypothesis": hypothesis,
                "start_date": datetime.fromisoformat(start_date),
                "end_date": datetime.fromisoformat(end_date),
                "metrics": metrics,
                "created_at": datetime.utcnow(),
                "status": "ACTIVE",
                "group_a_description": "Control - No AI prioritization",
                "group_b_description": "Treatment - With AI prioritization",
            }
            
            self.db["ab_experiments"].insert_one(experiment)
            logger.info(f"[ABTest] Experiment created: {experiment_id}")
            
            return {"created": True, "experiment_id": experiment_id}
        
        except Exception as e:
            logger.error(f"[ABTest] Error creating experiment: {e}")
            raise
    
    def track_metric(self, experiment_id: str, user_id: str, group: str,
                    metric_name: str, metric_value: float) -> Dict:
        """
        Record a metric observation for an experiment.
        
        Args:
            experiment_id: Experiment identifier
            user_id: User identifier
            group: "A" or "B"
            metric_name: Name of metric (completion_rate, time_hours, success_rate, csat)
            metric_value: Metric value (0-1 for rates, hours for time, 1-5 for CSAT)
        
        Returns:
            Dict with recording status
        """
        try:
            data = {
                "experiment_id": experiment_id,
                "user_id": user_id,
                "group": group,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "timestamp": datetime.utcnow(),
            }
            
            self.db["ab_experiment_data"].insert_one(data)
            logger.debug(f"[ABTest] Recorded {metric_name} for {user_id}: {metric_value}")
            
            return {"recorded": True, "metric_name": metric_name}
        
        except Exception as e:
            logger.error(f"[ABTest] Error tracking metric: {e}")
            raise
    
    def compute_t_test(self, group_a_values: List[float],
                      group_b_values: List[float]) -> Tuple[float, float]:
        """
        Compute t-test statistics between two groups.
        
        Returns:
            Tuple of (t_statistic, p_value)
        """
        try:
            if len(group_a_values) < 2 or len(group_b_values) < 2:
                return (0.0, 1.0)
            
            mean_a = mean(group_a_values)
            mean_b = mean(group_b_values)
            
            std_a = stdev(group_a_values) if len(group_a_values) > 1 else 0
            std_b = stdev(group_b_values) if len(group_b_values) > 1 else 0
            
            n_a = len(group_a_values)
            n_b = len(group_b_values)
            
            # Welch's t-test (doesn't assume equal variances)
            pooled_std = sqrt((std_a ** 2 / n_a) + (std_b ** 2 / n_b))
            
            if pooled_std == 0:
                t_stat = 0.0
            else:
                t_stat = (mean_b - mean_a) / pooled_std
            
            # Simplified p-value (two-tailed, approximate)
            # For real implementation, use scipy.stats.ttest_ind
            p_value = self._approximate_p_value(t_stat, n_a + n_b - 2)
            
            return (t_stat, p_value)
        
        except Exception as e:
            logger.error(f"[ABTest] Error computing t-test: {e}")
            return (0.0, 1.0)
    
    def _approximate_p_value(self, t_stat: float, df: int) -> float:
        """Approximate p-value from t-statistic (simplified)."""
        try:
            from scipy import stats
            return stats.t.sf(abs(t_stat), df) * 2  # Two-tailed
        except ImportError:
            # Simplified approximation without scipy
            abs_t = abs(t_stat)
            if abs_t > 3.0:
                return 0.01
            elif abs_t > 2.0:
                return 0.05
            elif abs_t > 1.5:
                return 0.15
            else:
                return 0.5
    
    def compute_cohens_d(self, group_a_values: List[float],
                        group_b_values: List[float]) -> float:
        """
        Compute Cohen's d effect size.
        
        Interpretation:
        - 0.2: Small effect
        - 0.5: Medium effect
        - 0.8: Large effect
        """
        try:
            if not group_a_values or not group_b_values:
                return 0.0
            
            mean_a = mean(group_a_values)
            mean_b = mean(group_b_values)
            
            std_a = stdev(group_a_values) if len(group_a_values) > 1 else 1
            std_b = stdev(group_b_values) if len(group_b_values) > 1 else 1
            
            n_a = len(group_a_values)
            n_b = len(group_b_values)
            
            # Pooled standard deviation
            pooled_std = sqrt(((n_a - 1) * std_a ** 2 + (n_b - 1) * std_b ** 2) / (n_a + n_b - 2))
            
            if pooled_std == 0:
                return 0.0
            
            return (mean_b - mean_a) / pooled_std
        
        except Exception as e:
            logger.error(f"[ABTest] Error computing Cohen's d: {e}")
            return 0.0
    
    def analyze_experiment(self, experiment_id: str,
                          metric_name: str) -> ExperimentResult:
        """
        Analyze experiment results for a specific metric.
        
        Args:
            experiment_id: Experiment identifier
            metric_name: Metric to analyze
        
        Returns:
            ExperimentResult with statistical analysis
        """
        try:
            logger.info(f"[ABTest] Analyzing {experiment_id} for metric {metric_name}")
            
            # Retrieve data
            data = list(self.db["ab_experiment_data"].find({
                "experiment_id": experiment_id,
                "metric_name": metric_name,
            }))
            
            if not data:
                logger.warning(f"[ABTest] No data found for {experiment_id}/{metric_name}")
                return ExperimentResult(
                    experiment_id=experiment_id,
                    group_a_mean=0.0, group_b_mean=0.0,
                    group_a_count=0, group_b_count=0,
                    t_statistic=0.0, p_value=1.0,
                    is_significant=False, effect_size=0.0,
                    confidence_interval=(0.0, 0.0),
                    winner=None,
                    recommendation="Insufficient data for analysis"
                )
            
            # Split by group
            group_a_values = [d["metric_value"] for d in data if d["group"] == ExperimentGroup.CONTROL]
            group_b_values = [d["metric_value"] for d in data if d["group"] == ExperimentGroup.TREATMENT]
            
            # Statistics
            mean_a = mean(group_a_values) if group_a_values else 0.0
            mean_b = mean(group_b_values) if group_b_values else 0.0
            
            t_stat, p_value = self.compute_t_test(group_a_values, group_b_values)
            effect_size = self.compute_cohens_d(group_a_values, group_b_values)
            
            # Confidence interval (95%)
            se_b = stdev(group_b_values) / sqrt(len(group_b_values)) if len(group_b_values) > 1 else 0
            ci_lower = mean_b - 1.96 * se_b
            ci_upper = mean_b + 1.96 * se_b
            
            # Interpretation
            is_significant = p_value < 0.05
            
            if not is_significant:
                winner = None
                recommendation = f"Not statistically significant (p={p_value:.3f}). Continue experiment."
            elif mean_b > mean_a:
                winner = "B"
                recommendation = f"Group B wins! {(mean_b - mean_a) / mean_a * 100:+.1f}% improvement (effect size: {effect_size:.2f})"
            else:
                winner = "A"
                recommendation = f"Group A wins! {(mean_a - mean_b) / mean_b * 100:+.1f}% improvement (effect size: {effect_size:.2f})"
            
            result = ExperimentResult(
                experiment_id=experiment_id,
                group_a_mean=mean_a,
                group_b_mean=mean_b,
                group_a_count=len(group_a_values),
                group_b_count=len(group_b_values),
                t_statistic=t_stat,
                p_value=p_value,
                is_significant=is_significant,
                effect_size=effect_size,
                confidence_interval=(ci_lower, ci_upper),
                winner=winner,
                recommendation=recommendation
            )
            
            logger.info(f"[ABTest] Analysis complete: {recommendation}")
            return result
        
        except Exception as e:
            logger.error(f"[ABTest] Error analyzing experiment: {e}")
            raise
    
    def get_experiment_status(self, experiment_id: str) -> Dict:
        """Get current status of an experiment."""
        try:
            experiment = self.db["ab_experiments"].find_one({"experiment_id": experiment_id})
            if not experiment:
                return {"found": False}
            
            # Count data points
            data_count = self.db["ab_experiment_data"].count_documents({
                "experiment_id": experiment_id
            })
            
            group_a_count = self.db["ab_experiment_data"].count_documents({
                "experiment_id": experiment_id,
                "group": ExperimentGroup.CONTROL
            })
            
            group_b_count = self.db["ab_experiment_data"].count_documents({
                "experiment_id": experiment_id,
                "group": ExperimentGroup.TREATMENT
            })
            
            return {
                "found": True,
                "experiment_id": experiment_id,
                "name": experiment.get("name"),
                "status": experiment.get("status"),
                "start_date": experiment.get("start_date").isoformat() if experiment.get("start_date") else None,
                "end_date": experiment.get("end_date").isoformat() if experiment.get("end_date") else None,
                "total_observations": data_count,
                "group_a_observations": group_a_count,
                "group_b_observations": group_b_count,
                "metrics": experiment.get("metrics", []),
            }
        
        except Exception as e:
            logger.error(f"[ABTest] Error getting experiment status: {e}")
            raise
    
    def should_enable_ai_prioritization(self, user_id: str,
                                       experiment_id: str = "prioritization_v1") -> bool:
        """
        Determine if AI prioritization should be enabled for user.
        
        Returns:
            True if user is in treatment group (B), False if in control (A)
        """
        group = self.assign_group(user_id, experiment_id)
        return group == ExperimentGroup.TREATMENT


# Singleton accessor
def get_ab_test_service() -> ABTestService:
    """Get or create the ABTestService singleton."""
    return ABTestService()
