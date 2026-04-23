"""
PRIORITIZATION ENGINE — Dynamic task ranking
Priority = (Impact × Success Probability × Urgency) / (Effort × Blockers)
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from services.mongodb_service import get_db

logger = logging.getLogger(__name__)


@dataclass
class RankedTask:
    """A task with computed priority rank."""
    task_id: str
    task_description: str
    priority_score: float
    rank: int
    impact: float
    success_probability: float
    urgency: float
    effort_hours: float
    blocker_count: int
    suggested_execution_sequence: List[str] = field(default_factory=list)
    justification: str = ""


class PrioritizationEngine:
    """
    Dynamic task prioritization based on impact, success probability, and effort.
    
    Formula:
        Priority = (Impact × Success_Prob × Urgency) / (Effort × max(Blockers, 1))
    
    Factors:
    - Impact: business value (0-1)
    - Success_Prob: from debate result (0-1)
    - Urgency: how soon deadline (0-1, higher = more urgent)
    - Effort: estimated hours (normalized)
    - Blockers: number of dependencies
    """

    def __init__(self, db=None):
        self.db = db or get_db()
        self.task_collection = self.db["tasks"]
        self.ranking_history = self.db["ranking_history"]

    def rank_tasks(
        self,
        tasks: List[Dict],
        forecasts: Dict[str, float]  # task_id → success_probability
    ) -> List[RankedTask]:
        """
        Rank a list of tasks by priority.
        
        Args:
            tasks: List of task documents from MongoDB
            forecasts: Mapping of task_id to success probability (from debate)
            
        Returns:
            List of RankedTask sorted by priority (highest first)
        """
        ranked = []
        
        for task in tasks:
            task_id = str(task.get("_id", task.get("task_id")))
            success_prob = forecasts.get(task_id, 0.5)
            
            # Extract factors
            impact = task.get("business_impact", 1.0)  # Default: neutral
            urgency = self._compute_urgency(task.get("deadline", None))
            effort = max(task.get("estimated_effort_hours", 10), 0.5)
            blockers = len(task.get("blockers", []))
            
            # Compute priority
            priority_score = self._compute_priority(
                impact=impact,
                success_prob=success_prob,
                urgency=urgency,
                effort=effort,
                blockers=blockers
            )
            
            justification = (
                f"Impact: {impact:.0%} | Success: {success_prob:.0%} | "
                f"Urgency: {urgency:.0%} | Effort: {effort:.0f}h | Blockers: {blockers}"
            )
            
            ranked_task = RankedTask(
                task_id=task_id,
                task_description=task.get("description", "")[:100],
                priority_score=priority_score,
                rank=0,  # Will be set after sorting
                impact=impact,
                success_probability=success_prob,
                urgency=urgency,
                effort_hours=effort,
                blocker_count=blockers,
                justification=justification
            )
            
            ranked.append(ranked_task)
        
        # Sort by priority (highest first)
        ranked.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Assign ranks
        for idx, task in enumerate(ranked, 1):
            task.rank = idx
            task.suggested_execution_sequence = self._suggest_execution_sequence(
                task, ranked
            )
        
        logger.info(f"[PrioritizationEngine] Ranked {len(ranked)} tasks")
        
        return ranked

    def _compute_urgency(self, deadline: Optional[str]) -> float:
        """
        Compute urgency based on deadline.
        
        Returns [0, 1] where 1 = most urgent.
        """
        if not deadline:
            return 0.2  # No deadline = low urgency
        
        try:
            deadline_dt = datetime.fromisoformat(deadline)
            now = datetime.utcnow()
            days_left = (deadline_dt - now).days
            
            if days_left <= 0:
                return 1.0  # Overdue = max urgency
            elif days_left <= 1:
                return 0.9  # Due today
            elif days_left <= 3:
                return 0.8  # Due within 3 days
            elif days_left <= 7:
                return 0.6  # Due within a week
            elif days_left <= 30:
                return 0.3  # Due within a month
            else:
                return 0.1  # Far future
        except:
            return 0.2

    def _compute_priority(
        self,
        impact: float,
        success_prob: float,
        urgency: float,
        effort: float,
        blockers: int
    ) -> float:
        """
        Compute priority score.
        
        Formula:
            Priority = (Impact × Success_Prob × Urgency) / (Effort / 10 × max(Blockers, 1))
        
        (Divided by Effort/10 to normalize; effort is in hours)
        """
        numerator = impact * success_prob * urgency
        denominator = max((effort / 10.0) * max(blockers, 1), 0.1)
        
        priority = numerator / denominator
        
        # Cap at reasonable range [0, 100]
        return min(max(priority, 0.0), 100.0)

    def _suggest_execution_sequence(
        self,
        task: RankedTask,
        all_ranked: List[RankedTask]
    ) -> List[str]:
        """
        Suggest optimal execution sequence for this task and related tasks.
        """
        sequence = [task.task_id]
        
        # Add highest-priority dependent tasks
        for other in all_ranked[:5]:  # Top 5
            if other.task_id != task.task_id:
                sequence.append(other.task_id)
        
        return sequence

    def should_break_into_subtasks(self, task: RankedTask) -> bool:
        """
        Recommend breaking into subtasks if effort is high and success low.
        """
        # Break if high effort + low success
        if task.effort_hours > 40 and task.success_probability < 0.6:
            return True
        
        # Break if many blockers
        if task.blocker_count > 3:
            return True
        
        return False

    def suggest_task_breakdown(
        self,
        task: RankedTask
    ) -> List[Dict]:
        """
        Suggest how to break a task into subtasks.
        """
        if not self.should_break_into_subtasks(task):
            return []
        
        suggestions = []
        
        # Strategy 1: Break by effort
        if task.effort_hours > 40:
            chunks = int(task.effort_hours / 20) + 1
            suggestions.append({
                "strategy": "break_by_effort",
                "description": f"Break into {chunks} subtasks (~20h each)",
                "rationale": "Reduce estimation risk and enable parallel work"
            })
        
        # Strategy 2: Break by milestone
        if task.blocker_count > 0:
            suggestions.append({
                "strategy": "break_by_milestone",
                "description": "Create milestone-based subtasks",
                "rationale": "Unblock downstream work earlier"
            })
        
        # Strategy 3: Break by risk
        if task.success_probability < 0.6:
            suggestions.append({
                "strategy": "break_by_risk",
                "description": "Separate risky components into separate tasks",
                "rationale": "Isolate and mitigate risk areas independently"
            })
        
        return suggestions

    def get_ranking_report(self) -> Dict:
        """Get summary statistics on recent rankings."""
        try:
            total_tasks = self.task_collection.count_documents({})
            high_priority = self.task_collection.count_documents(
                {"priority_score": {"$gte": 50}}
            )
            
            return {
                "total_tasks": total_tasks,
                "high_priority_count": high_priority,
                "high_priority_ratio": high_priority / total_tasks if total_tasks > 0 else 0,
            }
        except Exception as e:
            logger.error(f"[PrioritizationEngine] Error getting ranking report: {e}")
            return {}


# Singleton instance
_prioritizer = None


def get_prioritization_engine(db=None) -> PrioritizationEngine:
    """Get or create singleton PrioritizationEngine instance."""
    global _prioritizer
    if _prioritizer is None:
        _prioritizer = PrioritizationEngine(db=db)
    return _prioritizer
