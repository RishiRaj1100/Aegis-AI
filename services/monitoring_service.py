"""
AegisAI - Advanced Monitoring Service
Health checks, metrics, error tracking, performance monitoring, alerts
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class HealthCheckResult:
    """Health check result."""
    service: str
    status: HealthStatus
    response_time: float
    timestamp: datetime
    message: str
    checks: Dict[str, Any]


@dataclass
class Metric:
    """Performance metric."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str]


class AdvancedMonitoringService:
    """
    Advanced monitoring and observability.

    Features:
    - Health checks for all services
    - Performance metrics collection
    - Error tracking and alerting
    - Uptime monitoring
    - Usage analytics
    - Performance thresholds
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB."""
        self.db = db
        self.health_checks_collection = db["health_checks"]
        self.metrics_collection = db["metrics"]
        self.errors_collection = db["errors"]
        self.alerts_collection = db["alerts"]
        self.performance_collection = db["performance"]

        # In-memory metrics (for real-time tracking)
        self.memory_metrics: Dict[str, List[Metric]] = {}

    # ── Health Checks ─────────────────────────────────────────────────────────

    async def check_database_health(self) -> HealthCheckResult:
        """Check MongoDB connection health."""
        start = time.time()

        try:
            # Try to ping database
            await self.db.command("ping")
            response_time = time.time() - start

            result = HealthCheckResult(
                service="mongodb",
                status=HealthStatus.HEALTHY if response_time < 1 else HealthStatus.DEGRADED,
                response_time=response_time,
                timestamp=datetime.now(),
                message="Database responding normally" if response_time < 1 else "Database responding slowly",
                checks={
                    "ping": "success",
                    "response_time_ms": response_time * 1000,
                }
            )

            # Log result
            await self.health_checks_collection.insert_one(asdict(result))
            return result

        except Exception as e:
            response_time = time.time() - start

            return HealthCheckResult(
                service="mongodb",
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(),
                message=f"Database error: {str(e)}",
                checks={"error": str(e)}
            )

    async def check_redis_health(self, redis_client: Any) -> HealthCheckResult:
        """Check Redis connection health."""
        start = time.time()

        if redis_client is None:
            response_time = time.time() - start
            return HealthCheckResult(
                service="redis",
                status=HealthStatus.UNKNOWN,
                response_time=response_time,
                timestamp=datetime.now(),
                message="Redis client unavailable. Running without short-term cache.",
                checks={"ping": "unavailable"},
            )

        try:
            # Try to ping Redis
            result = await redis_client.ping()
            response_time = time.time() - start

            check_result = HealthCheckResult(
                service="redis",
                status=HealthStatus.HEALTHY if result else HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(),
                message="Redis responding normally" if result else "Redis not responding",
                checks={"ping": "pong" if result else "failed"}
            )

            await self.health_checks_collection.insert_one(asdict(check_result))
            return check_result

        except Exception as e:
            response_time = time.time() - start

            return HealthCheckResult(
                service="redis",
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(),
                message=f"Redis error: {str(e)}",
                checks={"error": str(e)}
            )

    async def check_api_health(self) -> HealthCheckResult:
        """Check API health."""
        try:
            # Check recent error rates
            recent_errors = await self.errors_collection.count_documents({
                "timestamp": {
                    "$gte": datetime.now() - timedelta(minutes=5)
                }
            })

            error_rate = recent_errors / 100  # Assume 100 requests per 5 min

            status = (
                HealthStatus.HEALTHY if error_rate < 0.05
                else HealthStatus.DEGRADED if error_rate < 0.10
                else HealthStatus.CRITICAL
            )

            return HealthCheckResult(
                service="api",
                status=status,
                response_time=0,
                timestamp=datetime.now(),
                message=f"API error rate: {error_rate * 100:.2f}%",
                checks={"error_rate": error_rate, "recent_errors": recent_errors}
            )

        except Exception as e:
            logger.error(f"Error checking API health: {e}")
            return HealthCheckResult(
                service="api",
                status=HealthStatus.UNKNOWN,
                response_time=0,
                timestamp=datetime.now(),
                message=f"Error checking API: {str(e)}",
                checks={"error": str(e)}
            )

    async def perform_full_health_check(
        self,
        redis_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        checks = {
            "database": await self.check_database_health(),
            "api": await self.check_api_health(),
        }

        if redis_client:
            checks["redis"] = await self.check_redis_health(redis_client)

        # Overall status
        statuses = [check.status for check in checks.values()]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: {
                    "status": check.status.value,
                    "response_time": check.response_time,
                    "message": check.message,
                    "details": check.checks,
                }
                for name, check in checks.items()
            }
        }

    # ── Metrics Collection ────────────────────────────────────────────────────

    async def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a performance metric."""
        try:
            metric = Metric(
                name=name,
                value=value,
                metric_type=metric_type,
                timestamp=datetime.now(),
                labels=labels or {}
            )

            # Store in database
            await self.metrics_collection.insert_one(asdict(metric))

            # Keep in memory for real-time tracking
            if name not in self.memory_metrics:
                self.memory_metrics[name] = []

            self.memory_metrics[name].append(metric)

            # Keep only last 1000 metrics per name
            if len(self.memory_metrics[name]) > 1000:
                self.memory_metrics[name] = self.memory_metrics[name][-1000:]

        except Exception as e:
            logger.error(f"Error recording metric: {e}")

    async def get_metric_stats(
        self,
        metric_name: str,
        hours: int = 1,
    ) -> Dict[str, Any]:
        """Get statistics for a metric over time period."""
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            metrics = await self.metrics_collection.find({
                "name": metric_name,
                "timestamp": {"$gte": start_time}
            }).to_list(None)

            if not metrics:
                return {}

            values = [m["value"] for m in metrics]

            return {
                "metric": metric_name,
                "period_hours": hours,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": sorted(values)[len(values) // 2],
                "p95": sorted(values)[int(len(values) * 0.95)],
                "p99": sorted(values)[int(len(values) * 0.99)],
            }

        except Exception as e:
            logger.error(f"Error getting metric stats: {e}")
            return {}

    # ── Error Tracking ────────────────────────────────────────────────────────

    async def record_error(
        self,
        error_type: str,
        message: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an error occurrence."""
        try:
            error_doc = {
                "error_type": error_type,
                "message": message,
                "user_id": user_id,
                "details": details or {},
                "timestamp": datetime.now(),
            }

            await self.errors_collection.insert_one(error_doc)

            # Check for alert conditions
            await self._check_error_thresholds(error_type)

        except Exception as e:
            logger.error(f"Error recording error: {e}")

    async def get_error_stats(self, hours: int = 1) -> Dict[str, Any]:
        """Get error statistics."""
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            # Count by error type
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_time}
                    }
                },
                {
                    "$group": {
                        "_id": "$error_type",
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}}
            ]

            error_counts = await self.errors_collection.aggregate(pipeline).to_list(None)

            total_errors = sum(ec["count"] for ec in error_counts)

            return {
                "period_hours": hours,
                "total_errors": total_errors,
                "by_type": error_counts,
            }

        except Exception as e:
            logger.error(f"Error getting error stats: {e}")
            return {}

    # ── Alerting ──────────────────────────────────────────────────────────────

    async def create_alert(
        self,
        title: str,
        message: str,
        severity: str,  # 'info', 'warning', 'critical'
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create an alert."""
        try:
            alert = {
                "title": title,
                "message": message,
                "severity": severity,
                "details": details or {},
                "created_at": datetime.now(),
                "acknowledged": False,
            }

            await self.alerts_collection.insert_one(alert)
            logger.warning(f"Alert created: {title} ({severity})")

        except Exception as e:
            logger.error(f"Error creating alert: {e}")

    async def _check_error_thresholds(self, error_type: str) -> None:
        """Check error thresholds and create alerts."""
        try:
            # Count errors in last 5 minutes
            recent_count = await self.errors_collection.count_documents({
                "error_type": error_type,
                "timestamp": {
                    "$gte": datetime.now() - timedelta(minutes=5)
                }
            })

            # Alert if threshold exceeded
            if recent_count > 10:
                await self.create_alert(
                    title=f"High Error Rate: {error_type}",
                    message=f"{recent_count} errors in last 5 minutes",
                    severity="critical",
                    details={"error_type": error_type, "count": recent_count}
                )

        except Exception as e:
            logger.error(f"Error checking thresholds: {e}")

    async def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        try:
            alerts = await self.alerts_collection.find().sort(
                "created_at", -1
            ).to_list(limit)

            return alerts

        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []

    # ── Performance Tracking ──────────────────────────────────────────────────

    async def record_request_performance(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[str] = None,
    ) -> None:
        """Record API request performance."""
        try:
            perf_doc = {
                "endpoint": endpoint,
                "method": method,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "user_id": user_id,
                "timestamp": datetime.now(),
            }

            await self.performance_collection.insert_one(perf_doc)

            # Record as metric
            await self.record_metric(
                f"request_{method}_{endpoint}",
                duration_ms,
                MetricType.TIMER,
                {"status": str(status_code)}
            )

        except Exception as e:
            logger.error(f"Error recording performance: {e}")

    async def get_performance_stats(self, hours: int = 1) -> Dict[str, Any]:
        """Get API performance statistics."""
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            # Get request stats by endpoint
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": start_time}
                    }
                },
                {
                    "$group": {
                        "_id": {"endpoint": "$endpoint", "method": "$method"},
                        "count": {"$sum": 1},
                        "avg_duration": {"$avg": "$duration_ms"},
                        "max_duration": {"$max": "$duration_ms"},
                        "min_duration": {"$min": "$duration_ms"},
                        "error_count": {
                            "$sum": {
                                "$cond": [{"$gte": ["$status_code", 400]}, 1, 0]
                            }
                        }
                    }
                },
                {"$sort": {"count": -1}}
            ]

            stats = await self.performance_collection.aggregate(pipeline).to_list(None)

            return {
                "period_hours": hours,
                "endpoints": stats,
            }

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {}

    # ── Uptime Tracking ───────────────────────────────────────────────────────

    async def get_uptime_percentage(self, days: int = 7) -> float:
        """Get system uptime percentage."""
        try:
            start_time = datetime.now() - timedelta(days=days)

            healthy_checks = await self.health_checks_collection.count_documents({
                "status": HealthStatus.HEALTHY.value,
                "timestamp": {"$gte": start_time}
            })

            total_checks = await self.health_checks_collection.count_documents({
                "timestamp": {"$gte": start_time}
            })

            if total_checks == 0:
                return 100.0

            return (healthy_checks / total_checks) * 100

        except Exception as e:
            logger.error(f"Error calculating uptime: {e}")
            return 0.0

    # ── Dashboard Data ────────────────────────────────────────────────────────

    async def get_monitoring_dashboard(
        self,
        redis_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        try:
            # Perform health check
            health = await self.perform_full_health_check(redis_client)

            # Get error stats
            error_stats = await self.get_error_stats(hours=1)

            # Get performance stats
            perf_stats = await self.get_performance_stats(hours=1)

            # Get uptime
            uptime = await self.get_uptime_percentage(days=7)

            # Get recent alerts
            alerts = await self.get_recent_alerts(limit=10)

            return {
                "timestamp": datetime.now().isoformat(),
                "health": health,
                "errors": error_stats,
                "performance": perf_stats,
                "uptime_7d": uptime,
                "recent_alerts": alerts,
            }

        except Exception as e:
            logger.error(f"Error building dashboard: {e}")
            return {}


def get_monitoring_service(db: AsyncIOMotorDatabase) -> AdvancedMonitoringService:
    """Get monitoring service instance."""
    return AdvancedMonitoringService(db)
