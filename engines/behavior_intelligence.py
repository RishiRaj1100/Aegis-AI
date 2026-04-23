"""
BEHAVIOR INTELLIGENCE ENGINE — Track Task Delays and Abandonment Patterns

Purpose: Predict task delays and detect abandonment risk based on historical behavior
Outputs: delay_probability, abandonment_risk, reordering_recommendations
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from statistics import mean, stdev

from services.mongodb_service import get_db

logger = logging.getLogger(__name__)


class AbandonmentRisk(Enum):
    """Abandonment risk levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DelayPattern(Enum):
    """Common delay patterns."""
    NO_DELAY = "NO_DELAY"
    MINOR_DELAY = "MINOR_DELAY"
    SIGNIFICANT_DELAY = "SIGNIFICANT_DELAY"
    EXTREME_DELAY = "EXTREME_DELAY"
    ABANDONED = "ABANDONED"


@dataclass
class BehaviorAnalysis:
    """Analysis of task behavior."""
    task_id: str
    delay_probability: float  # 0-1: probability of delay > 20%
    delay_days: float  # estimated days of delay
    delay_pattern: DelayPattern
    abandonment_risk: AbandonmentRisk
    abandonment_probability: float  # 0-1
    time_to_first_action: float  # average hours from creation to first action
    completion_time_estimate: float  # estimated hours to complete
    reorder_recommendation: str  # "MOVE_UP", "MOVE_DOWN", "KEEP", "BREAK_INTO_SUBTASKS"
    risk_factors: List[str] = field(default_factory=list)
    success_indicators: List[str] = field(default_factory=list)
    mitigation_suggestions: List[str] = field(default_factory=list)
    confidence_score: float = 0.8


@dataclass
class TaskBehaviorProfile:
    """Historical behavior profile for a task."""
    task_id: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    abandoned_at: Optional[datetime]
    
    # Timing metrics (hours)
    time_to_first_action: Optional[float]  # hours from creation to start
    time_between_steps: Optional[float]  # average hours between actions
    total_execution_time: Optional[float]  # hours from start to finish
    
    # Status
    is_completed: bool = False
    is_abandoned: bool = False
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, ABANDONED
    
    # Task characteristics
    complexity: float = 0.5  # 0-1
    team_size: int = 1
    effort_estimate_hours: float = 10.0
    actual_effort_hours: Optional[float] = None
    deadline: Optional[datetime] = None


class BehaviorIntelligenceEngine:
    """Autonomous behavior intelligence system for delay/abandonment prediction."""
    
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
        logger.info("[BehaviorIntelligence] Engine initialized")
    
    def _setup_collections(self):
        """Setup MongoDB collections with indexes."""
        behaviors = self.db["task_behaviors"]
        behaviors.create_index([("task_id", 1)])
        behaviors.create_index([("created_at", -1)])
        behaviors.create_index([("is_abandoned", 1)])
        
        delay_patterns = self.db["delay_patterns"]
        delay_patterns.create_index([("user_id", 1)])
        delay_patterns.create_index([("task_type", 1)])
    
    def record_task_start(self, task_id: str, user_id: str, complexity: float, 
                          team_size: int, effort_estimate: float,
                          deadline: Optional[str] = None) -> Dict:
        """Record task creation/start event."""
        try:
            now = datetime.utcnow()
            
            profile = TaskBehaviorProfile(
                task_id=task_id,
                created_at=now,
                started_at=now,
                complexity=complexity,
                team_size=team_size,
                effort_estimate_hours=effort_estimate,
                deadline=datetime.fromisoformat(deadline) if deadline else None,
                status="IN_PROGRESS"
            )
            
            self.db["task_behaviors"].insert_one({
                "task_id": task_id,
                "user_id": user_id,
                "created_at": profile.created_at,
                "started_at": profile.started_at,
                "time_to_first_action": 0.0,  # Started immediately
                "complexity": profile.complexity,
                "team_size": profile.team_size,
                "effort_estimate_hours": profile.effort_estimate_hours,
                "deadline": profile.deadline,
                "status": "IN_PROGRESS",
                "is_completed": False,
                "is_abandoned": False,
                "last_activity": now,
                "activity_log": [{"event": "STARTED", "timestamp": now}]
            })
            
            logger.info(f"[BehaviorIntelligence] Task {task_id} started")
            return {"recorded": True, "task_id": task_id}
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error recording task start: {e}")
            raise
    
    def record_task_activity(self, task_id: str, activity: str) -> Dict:
        """Record task activity (step taken, progress made)."""
        try:
            now = datetime.utcnow()
            
            self.db["task_behaviors"].update_one(
                {"task_id": task_id},
                {
                    "$push": {"activity_log": {"event": activity, "timestamp": now}},
                    "$set": {"last_activity": now}
                }
            )
            
            logger.info(f"[BehaviorIntelligence] Activity recorded for {task_id}: {activity}")
            return {"recorded": True, "activity": activity}
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error recording activity: {e}")
            raise
    
    def record_task_completion(self, task_id: str, actual_effort_hours: float,
                               actual_completion_time: Optional[float] = None) -> Dict:
        """Record task completion."""
        try:
            now = datetime.utcnow()
            
            result = self.db["task_behaviors"].update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "completed_at": now,
                        "actual_effort_hours": actual_effort_hours,
                        "status": "COMPLETED",
                        "is_completed": True,
                    }
                }
            )
            
            logger.info(f"[BehaviorIntelligence] Task {task_id} completed")
            return {"recorded": True, "task_id": task_id, "matched_count": result.matched_count}
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error recording completion: {e}")
            raise
    
    def detect_abandonment(self, task_id: str, inactivity_threshold_days: int = 7) -> Dict:
        """
        Detect if task is abandoned (no activity for threshold days).
        
        Args:
            task_id: Task identifier
            inactivity_threshold_days: Days without activity to mark as abandoned
        
        Returns:
            Dict with is_abandoned (bool), days_inactive, recommendation
        """
        try:
            task = self.db["task_behaviors"].find_one({"task_id": task_id})
            if not task:
                return {"is_abandoned": False, "reason": "Task not found"}
            
            # Already completed - not abandoned
            if task.get("is_completed"):
                return {"is_abandoned": False, "reason": "Task completed"}
            
            # Check inactivity period
            last_activity = task.get("last_activity", task.get("created_at"))
            if not last_activity:
                return {"is_abandoned": False, "reason": "No activity data"}
            
            now = datetime.utcnow()
            inactivity_duration = now - last_activity
            days_inactive = inactivity_duration.days
            
            is_abandoned = days_inactive >= inactivity_threshold_days
            
            if is_abandoned:
                logger.warning(f"[BehaviorIntelligence] Task {task_id} detected as abandoned")
                self.db["task_behaviors"].update_one(
                    {"task_id": task_id},
                    {
                        "$set": {
                            "is_abandoned": True,
                            "abandoned_at": now,
                            "status": "ABANDONED"
                        }
                    }
                )
            
            return {
                "is_abandoned": is_abandoned,
                "days_inactive": days_inactive,
                "threshold_days": inactivity_threshold_days
            }
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error detecting abandonment: {e}")
            raise
    
    def predict_delay(self, task_id: str, task_features: Dict,
                      user_id: Optional[str] = None) -> Tuple[float, float, str]:
        """
        Predict probability of task delay and estimated delay days.
        
        Formula: delay_prob = f(complexity, effort, urgency, team_experience, history)
        
        Returns:
            Tuple of (delay_probability, estimated_delay_days, pattern)
        """
        try:
            # Get task info
            task = self.db["task_behaviors"].find_one({"task_id": task_id})
            if not task:
                # New task - use baseline
                complexity = task_features.get("complexity", 0.5)
                effort = task_features.get("effort_estimate_hours", 10)
                delay_prob = 0.1 + (complexity * 0.3)  # 10-40% baseline
                return (delay_prob, delay_prob * 2, DelayPattern.MINOR_DELAY.value)
            
            # Get historical patterns for user
            user_patterns = list(self.db["task_behaviors"].find(
                {"user_id": user_id} if user_id else {}
            ).sort("created_at", -1).limit(10))
            
            # Calculate metrics
            complexity = task.get("complexity", 0.5)
            effort = task.get("effort_estimate_hours", 10)
            team_size = task.get("team_size", 1)
            
            # Risk factors
            delay_factors = 0.0
            
            # 1. Complexity factor (high complexity = more delays)
            delay_factors += complexity * 0.3
            
            # 2. Team factor (larger teams = more coordination = more delays)
            team_factor = min(team_size * 0.1, 0.3)  # Cap at 0.3
            delay_factors += team_factor
            
            # 3. Historical factor (if user has history of delays)
            if user_patterns:
                delayed_tasks = sum(1 for p in user_patterns if p.get("actual_effort_hours", 0) > p.get("effort_estimate_hours", 1) * 1.2)
                delay_rate = delayed_tasks / len(user_patterns)
                delay_factors += delay_rate * 0.2
            
            # 4. Urgency factor (tight deadlines increase delay risk)
            if task.get("deadline"):
                deadline = task["deadline"]
                now = datetime.utcnow()
                days_to_deadline = (deadline - now).days
                days_available = max(days_to_deadline, 1)
                effort_days = effort / 8  # Assuming 8-hour workday
                if effort_days > days_available:
                    urgency_factor = min((effort_days / days_available - 1) * 0.2, 0.3)
                    delay_factors += urgency_factor
            
            # Normalize to 0-1
            delay_probability = min(max(delay_factors, 0.05), 0.95)
            estimated_delay_days = delay_probability * (effort / 8)
            
            # Determine pattern
            if delay_probability < 0.2:
                pattern = DelayPattern.NO_DELAY.value
            elif delay_probability < 0.4:
                pattern = DelayPattern.MINOR_DELAY.value
            elif delay_probability < 0.6:
                pattern = DelayPattern.SIGNIFICANT_DELAY.value
            else:
                pattern = DelayPattern.EXTREME_DELAY.value
            
            logger.info(f"[BehaviorIntelligence] Delay prediction for {task_id}: {delay_probability:.0%}")
            
            return (delay_probability, estimated_delay_days, pattern)
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error predicting delay: {e}")
            return (0.5, 2.0, DelayPattern.SIGNIFICANT_DELAY.value)
    
    def predict_abandonment(self, task_id: str, task_features: Dict,
                            user_id: Optional[str] = None) -> Tuple[float, AbandonmentRisk]:
        """
        Predict abandonment probability based on task characteristics and user history.
        
        Formula: abandonment_prob = f(complexity, effort, team_experience, urgency, history)
        
        Returns:
            Tuple of (abandonment_probability, risk_level)
        """
        try:
            task = self.db["task_behaviors"].find_one({"task_id": task_id})
            if not task:
                return (0.1, AbandonmentRisk.LOW)
            
            complexity = task.get("complexity", 0.5)
            effort = task.get("effort_estimate_hours", 10)
            team_size = task.get("team_size", 1)
            
            # Abandonment factors
            abandonment_factors = 0.0
            risk_factors = []
            
            # 1. Complexity factor (very complex tasks = more abandonment)
            if complexity > 0.7:
                abandonment_factors += 0.25
                risk_factors.append(f"High complexity ({complexity:.0%})")
            
            # 2. Effort factor (very large tasks = more abandonment)
            if effort > 80:
                abandonment_factors += 0.2
                risk_factors.append(f"Large effort ({effort} hours)")
            
            # 3. No deadline (no urgency = more abandonment)
            if not task.get("deadline"):
                abandonment_factors += 0.15
                risk_factors.append("No deadline set")
            
            # 4. Team factor (solo work = lower abandonment than expected)
            if team_size == 1:
                abandonment_factors -= 0.05  # Slight reduction for solo work
            
            # 5. Historical abandonment rate
            if user_id:
                user_tasks = list(self.db["task_behaviors"].find(
                    {"user_id": user_id}
                ).sort("created_at", -1).limit(20))
                
                if user_tasks:
                    abandoned_count = sum(1 for t in user_tasks if t.get("is_abandoned"))
                    abandonment_rate = abandoned_count / len(user_tasks)
                    
                    if abandonment_rate > 0.3:
                        abandonment_factors += 0.3
                        risk_factors.append(f"High user abandonment rate ({abandonment_rate:.0%})")
                    elif abandonment_rate > 0.1:
                        abandonment_factors += 0.1
                        risk_factors.append(f"Moderate abandonment rate ({abandonment_rate:.0%})")
            
            # Normalize
            abandonment_probability = min(max(abandonment_factors, 0.01), 0.95)
            
            # Risk level
            if abandonment_probability < 0.1:
                risk_level = AbandonmentRisk.LOW
            elif abandonment_probability < 0.3:
                risk_level = AbandonmentRisk.MEDIUM
            elif abandonment_probability < 0.6:
                risk_level = AbandonmentRisk.HIGH
            else:
                risk_level = AbandonmentRisk.CRITICAL
            
            logger.info(f"[BehaviorIntelligence] Abandonment risk for {task_id}: {risk_level.value}")
            
            return (abandonment_probability, risk_level)
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error predicting abandonment: {e}")
            return (0.3, AbandonmentRisk.MEDIUM)
    
    def analyze_task_behavior(self, task_id: str, task_features: Dict,
                              user_id: Optional[str] = None) -> BehaviorAnalysis:
        """
        Complete behavior analysis combining delay and abandonment predictions.
        
        Returns: BehaviorAnalysis with full insights
        """
        try:
            # Get predictions
            delay_prob, delay_days, delay_pattern = self.predict_delay(task_id, task_features, user_id)
            abandon_prob, abandon_risk = self.predict_abandonment(task_id, task_features, user_id)
            
            # Collect task data
            task = self.db["task_behaviors"].find_one({"task_id": task_id})
            
            # Determine recommendations
            if delay_prob > 0.6 and task_features.get("effort_estimate_hours", 10) > 40:
                reorder_recommendation = "BREAK_INTO_SUBTASKS"
            elif abandon_risk in [AbandonmentRisk.HIGH, AbandonmentRisk.CRITICAL]:
                reorder_recommendation = "MOVE_UP"  # Prioritize to reduce abandonment
            elif delay_prob > 0.5:
                reorder_recommendation = "MOVE_UP"  # Prioritize earlier to get ahead
            else:
                reorder_recommendation = "KEEP"
            
            # Mitigation suggestions
            mitigations = []
            if delay_prob > 0.5:
                mitigations.append("Increase buffer time by 20-30%")
            if abandon_risk == AbandonmentRisk.CRITICAL:
                mitigations.append("Break into smaller milestones")
                mitigations.append("Assign dedicated owner")
            if task_features.get("effort_estimate_hours", 10) > 80:
                mitigations.append("Consider breaking into subtasks")
            
            # Risk factors
            risk_factors = []
            if delay_prob > 0.7:
                risk_factors.append("Very high delay risk")
            if abandon_risk in [AbandonmentRisk.HIGH, AbandonmentRisk.CRITICAL]:
                risk_factors.append(f"High abandonment risk ({abandon_prob:.0%})")
            if task_features.get("complexity", 0.5) > 0.7:
                risk_factors.append("High task complexity")
            
            # Success indicators
            success_indicators = []
            if delay_prob < 0.3:
                success_indicators.append("Low delay risk")
            if abandon_risk == AbandonmentRisk.LOW:
                success_indicators.append("Low abandonment risk")
            if task_features.get("team_size", 1) > 1:
                success_indicators.append("Team allocated")
            
            analysis = BehaviorAnalysis(
                task_id=task_id,
                delay_probability=delay_prob,
                delay_days=delay_days,
                delay_pattern=DelayPattern(delay_pattern),
                abandonment_risk=abandon_risk,
                abandonment_probability=abandon_prob,
                time_to_first_action=task.get("time_to_first_action", 0) if task else 0,
                completion_time_estimate=task_features.get("effort_estimate_hours", 10),
                reorder_recommendation=reorder_recommendation,
                risk_factors=risk_factors,
                success_indicators=success_indicators,
                mitigation_suggestions=mitigations,
                confidence_score=0.82
            )
            
            logger.info(f"[BehaviorIntelligence] Analysis complete for {task_id}")
            return analysis
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error in behavior analysis: {e}")
            raise
    
    def suggest_task_reordering(self, tasks: List[Dict],
                               forecasts: Dict[str, float]) -> List[Tuple[str, str]]:
        """
        Suggest task reordering to minimize abandonment and delays.
        
        Args:
            tasks: List of task dicts
            forecasts: Dict of task_id -> success_probability
        
        Returns:
            List of (task_id, recommendation) tuples
        """
        try:
            suggestions = []
            
            for task in tasks:
                task_id = task["task_id"]
                analysis = self.analyze_task_behavior(
                    task_id=task_id,
                    task_features={
                        "complexity": task.get("complexity", 0.5),
                        "effort_estimate_hours": task.get("effort_estimate_hours", 10),
                        "team_size": task.get("team_size", 1),
                    }
                )
                
                suggestions.append((task_id, analysis.reorder_recommendation))
            
            logger.info(f"[BehaviorIntelligence] Reordering suggestions for {len(tasks)} tasks")
            return suggestions
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error suggesting reordering: {e}")
            raise
    
    def get_behavior_statistics(self, user_id: str) -> Dict:
        """Get aggregated behavior statistics for a user."""
        try:
            tasks = list(self.db["task_behaviors"].find(
                {"user_id": user_id}
            ))
            
            if not tasks:
                return {"user_id": user_id, "task_count": 0}
            
            # Calculate statistics
            completed = sum(1 for t in tasks if t.get("is_completed"))
            abandoned = sum(1 for t in tasks if t.get("is_abandoned"))
            
            delay_rates = []
            for t in tasks:
                if t.get("actual_effort_hours") and t.get("effort_estimate_hours"):
                    delay_rate = t["actual_effort_hours"] / t["effort_estimate_hours"]
                    delay_rates.append(delay_rate)
            
            stats = {
                "user_id": user_id,
                "total_tasks": len(tasks),
                "completed_tasks": completed,
                "abandoned_tasks": abandoned,
                "abandoned_rate": abandoned / len(tasks) if tasks else 0,
                "avg_delay_factor": mean(delay_rates) if delay_rates else 1.0,
                "delay_std_dev": stdev(delay_rates) if len(delay_rates) > 1 else 0,
            }
            
            logger.info(f"[BehaviorIntelligence] Stats for {user_id}: {abandoned}/{len(tasks)} abandoned")
            return stats
        
        except Exception as e:
            logger.error(f"[BehaviorIntelligence] Error getting statistics: {e}")
            raise


# Singleton accessor
def get_behavior_intelligence_engine() -> BehaviorIntelligenceEngine:
    """Get or create the BehaviorIntelligenceEngine singleton."""
    return BehaviorIntelligenceEngine()
