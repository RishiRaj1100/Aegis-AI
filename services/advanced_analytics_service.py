"""
AegisAI - Advanced Analytics Service
Custom dashboards, trend analysis, export functionality, metrics aggregation
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class TimePeriod(str, Enum):
    """Time period for analytics."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


class AdvancedAnalyticsService:
    """
    Advanced analytics with filtering, trends, and export.

    Features:
    - Custom date range filtering
    - Trend analysis over time
    - Domain-based performance
    - Confidence distribution
    - CSV/JSON export
    - Real-time aggregation
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB connection."""
        self.db = db
        self.tasks_collection = db["tasks"]
        self.analytics_cache = db["analytics_cache"]

    # ── Time Range Filtering ──────────────────────────────────────────────────

    async def get_analytics_for_period(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        domain_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get analytics for custom date range.

        Args:
            user_id: User ID
            start_date: Start of period
            end_date: End of period
            domain_filter: Optional domain to filter by
            status_filter: Optional status to filter by

        Returns:
            Aggregated analytics for period
        """
        try:
            query: Dict[str, Any] = {
                "user_id": user_id,
                "created_at": {
                    "$gte": start_date,
                    "$lte": end_date,
                }
            }

            if domain_filter:
                query["domain"] = domain_filter

            if status_filter:
                query["status"] = status_filter

            tasks = await self.tasks_collection.find(query).to_list(None)

            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "kpis": await self._calculate_kpis(tasks),
                "risk_distribution": await self._calculate_risk_distribution(tasks),
                "domain_distribution": await self._calculate_domain_distribution(tasks),
                "confidence_histogram": await self._calculate_confidence_histogram(tasks),
                "timeline": await self._calculate_timeline(tasks),
                "task_count": len(tasks),
            }

        except Exception as e:
            logger.error(f"Error getting period analytics: {e}")
            return {}

    async def get_quick_period(
        self,
        user_id: str,
        period: TimePeriod,
    ) -> Dict[str, Any]:
        """Get analytics for predefined time period."""
        end_date = datetime.now()

        if period == TimePeriod.DAY:
            start_date = end_date - timedelta(days=1)
        elif period == TimePeriod.WEEK:
            start_date = end_date - timedelta(weeks=1)
        elif period == TimePeriod.MONTH:
            start_date = end_date - timedelta(days=30)
        elif period == TimePeriod.QUARTER:
            start_date = end_date - timedelta(days=90)
        elif period == TimePeriod.YEAR:
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        return await self.get_analytics_for_period(user_id, start_date, end_date)

    # ── Trend Analysis ────────────────────────────────────────────────────────

    async def get_trends(
        self,
        user_id: str,
        metric: str,  # 'confidence', 'trust_score', 'completion_rate'
        days: int = 30,
        granularity: str = "daily",  # daily, weekly, monthly
    ) -> List[Dict[str, Any]]:
        """
        Get trend data for metric over time.

        Returns time series data for charting.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            query = {
                "user_id": user_id,
                "created_at": {
                    "$gte": start_date,
                    "$lte": end_date,
                }
            }

            tasks = await self.tasks_collection.find(query).to_list(None)

            # Group by time period
            trends = {}

            for task in tasks:
                if granularity == "daily":
                    bucket = task["created_at"].date()
                elif granularity == "weekly":
                    bucket = task["created_at"].isocalendar()[1]
                else:  # monthly
                    bucket = task["created_at"].month

                if bucket not in trends:
                    trends[bucket] = []

                if metric == "confidence":
                    trends[bucket].append(task.get("confidence_score", 0))
                elif metric == "trust_score":
                    trends[bucket].append(task.get("trust_score", 0))
                elif metric == "completion_rate":
                    trends[bucket].append(1 if task.get("status") == "completed" else 0)

            # Calculate averages
            result = []
            for bucket in sorted(trends.keys()):
                values = trends[bucket]
                result.append({
                    "period": str(bucket),
                    "value": sum(values) / len(values) if values else 0,
                    "count": len(values),
                })

            return result

        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return []

    # ── Domain Performance ────────────────────────────────────────────────────

    async def get_domain_performance(
        self,
        user_id: str,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics per domain.

        Returns ranking of domains by performance.
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            tasks = await self.tasks_collection.find({
                "user_id": user_id,
                "created_at": {
                    "$gte": start_date,
                    "$lte": end_date,
                }
            }).to_list(None)

            # Group by domain
            domains = {}
            for task in tasks:
                domain = task.get("domain", "uncategorized")

                if domain not in domains:
                    domains[domain] = {
                        "domain": domain,
                        "total_tasks": 0,
                        "completed": 0,
                        "avg_confidence": 0,
                        "avg_trust_score": 0,
                        "confidence_scores": [],
                        "trust_scores": [],
                    }

                domains[domain]["total_tasks"] += 1
                if task.get("status") == "completed":
                    domains[domain]["completed"] += 1

                conf = task.get("confidence_score", 0)
                trust = task.get("trust_score", 0)

                domains[domain]["confidence_scores"].append(conf)
                domains[domain]["trust_scores"].append(trust)

            # Calculate averages and rates
            result = []
            for domain, data in domains.items():
                result.append({
                    "domain": domain,
                    "total_tasks": data["total_tasks"],
                    "completed_tasks": data["completed"],
                    "completion_rate": (data["completed"] / data["total_tasks"] * 100)
                        if data["total_tasks"] > 0 else 0,
                    "avg_confidence": sum(data["confidence_scores"]) / len(data["confidence_scores"])
                        if data["confidence_scores"] else 0,
                    "avg_trust_score": sum(data["trust_scores"]) / len(data["trust_scores"])
                        if data["trust_scores"] else 0,
                })

            # Sort by completion rate
            return sorted(result, key=lambda x: x["completion_rate"], reverse=True)

        except Exception as e:
            logger.error(f"Error getting domain performance: {e}")
            return []

    # ── Export Functions ──────────────────────────────────────────────────────

    async def export_tasks_csv(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Export tasks to CSV format.

        Returns CSV string.
        """
        try:
            query = {"user_id": user_id}

            if start_date and end_date:
                query["created_at"] = {
                    "$gte": start_date,
                    "$lte": end_date,
                }

            tasks = await self.tasks_collection.find(query).to_list(None)

            # Build CSV
            csv_lines = [
                "task_id,goal,domain,priority,status,confidence_score,trust_score,created_at"
            ]

            for task in tasks:
                csv_lines.append(
                    f'"{task.get("task_id")}","{task.get("goal")}","{task.get("domain")}",'
                    f'"{task.get("priority")}","{task.get("status")}",'
                    f'{task.get("confidence_score", 0)},{task.get("trust_score", 0)},'
                    f'"{task.get("created_at")}"'
                )

            return "\n".join(csv_lines)

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return ""

    async def export_analytics_json(
        self,
        user_id: str,
        period: TimePeriod = TimePeriod.MONTH,
    ) -> Dict[str, Any]:
        """Export analytics as JSON."""
        return await self.get_quick_period(user_id, period)

    # ── Helper Methods ────────────────────────────────────────────────────────

    async def _calculate_kpis(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate key performance indicators."""
        if not tasks:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0,
                "avg_confidence": 0,
                "avg_trust_score": 0,
                "avg_time_to_completion": 0,
            }

        completed = [t for t in tasks if t.get("status") == "completed"]
        confidence_scores = [t.get("confidence_score", 0) for t in tasks]
        trust_scores = [t.get("trust_score", 0) for t in tasks]

        return {
            "total_tasks": len(tasks),
            "completed_tasks": len(completed),
            "completion_rate": (len(completed) / len(tasks) * 100) if tasks else 0,
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "avg_trust_score": sum(trust_scores) / len(trust_scores) if trust_scores else 0,
            "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
        }

    async def _calculate_risk_distribution(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Calculate risk level distribution."""
        distribution = {"high": 0, "medium": 0, "low": 0}

        for task in tasks:
            conf = task.get("confidence_score", 50)
            if conf < 45:
                distribution["high"] += 1
            elif conf < 72:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1

        return distribution

    async def _calculate_domain_distribution(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Calculate task distribution by domain."""
        distribution = {}

        for task in tasks:
            domain = task.get("domain", "uncategorized")
            distribution[domain] = distribution.get(domain, 0) + 1

        return distribution

    async def _calculate_confidence_histogram(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Calculate confidence score distribution (histogram bins)."""
        bins = {
            "0-20": 0,
            "20-40": 0,
            "40-60": 0,
            "60-80": 0,
            "80-100": 0,
        }

        for task in tasks:
            conf = task.get("confidence_score", 50)
            if conf < 20:
                bins["0-20"] += 1
            elif conf < 40:
                bins["20-40"] += 1
            elif conf < 60:
                bins["40-60"] += 1
            elif conf < 80:
                bins["60-80"] += 1
            else:
                bins["80-100"] += 1

        return bins

    async def _calculate_timeline(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Calculate timeline (tasks per day)."""
        timeline = {}

        for task in tasks:
            date = task.get("created_at", datetime.now()).date()
            timeline[date] = timeline.get(date, 0) + 1

        return [
            {"date": str(date), "count": count}
            for date, count in sorted(timeline.items())
        ]


def get_analytics_service(db: AsyncIOMotorDatabase) -> AdvancedAnalyticsService:
    """Get analytics service instance."""
    return AdvancedAnalyticsService(db)
