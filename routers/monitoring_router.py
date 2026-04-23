"""
Monitoring API Router
Health checks, metrics, alerts, performance monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from services.mongodb_service import get_mongodb_service
from services.redis_service import get_redis_service
from services.monitoring_service import (
    AdvancedMonitoringService,
    MetricType,
    get_monitoring_service,
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    try:
        return get_mongodb_service().db
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def get_redis() -> Redis | None:
    """Get Redis client."""
    return get_redis_service().client


# ── Health Checks ────────────────────────────────────────────────────────────

@router.get("/health")
async def get_full_health_check(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    """Perform comprehensive health check."""
    try:
        service = get_monitoring_service(db)

        health = await service.perform_full_health_check(redis_client)

        return health

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/database")
async def check_database_health(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Check database health."""
    try:
        service = get_monitoring_service(db)

        result = await service.check_database_health()

        return {
            "status": "success",
            "service": result.service,
            "health_status": result.status.value,
            "response_time_ms": result.response_time * 1000,
            "message": result.message,
            "checks": result.checks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/redis")
async def check_redis_health(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis_client: Redis | None = Depends(get_redis),
):
    """Check Redis health."""
    try:
        service = get_monitoring_service(db)

        result = await service.check_redis_health(redis_client)

        return {
            "status": "success",
            "service": result.service,
            "health_status": result.status.value,
            "response_time_ms": result.response_time * 1000,
            "message": result.message,
            "checks": result.checks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/api")
async def check_api_health(
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Check API health."""
    try:
        service = get_monitoring_service(db)

        result = await service.check_api_health()

        return {
            "status": "success",
            "service": result.service,
            "health_status": result.status.value,
            "message": result.message,
            "checks": result.checks,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Metrics ──────────────────────────────────────────────────────────────────

@router.post("/metrics/record")
async def record_metric(
    name: str = Query(...),
    value: float = Query(...),
    metric_type: str = Query("gauge", description="counter, gauge, histogram, timer"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Record a performance metric."""
    try:
        service = get_monitoring_service(db)

        metric_type_enum = MetricType(metric_type)

        await service.record_metric(name, value, metric_type_enum)

        return {
            "status": "success",
            "metric": name,
            "value": value,
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric type: {metric_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{metric_name}/stats")
async def get_metric_stats(
    metric_name: str,
    hours: int = Query(1, ge=1, le=168),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get statistics for a metric."""
    try:
        service = get_monitoring_service(db)

        stats = await service.get_metric_stats(metric_name, hours)

        return {
            "status": "success",
            "metric": metric_name,
            "stats": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Error Tracking ───────────────────────────────────────────────────────────

@router.post("/errors/record")
async def record_error(
    error_type: str = Query(...),
    message: str = Query(...),
    user_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Record an error."""
    try:
        service = get_monitoring_service(db)

        await service.record_error(
            error_type=error_type,
            message=message,
            user_id=user_id,
        )

        return {
            "status": "success",
            "message": "Error recorded",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors/stats")
async def get_error_stats(
    hours: int = Query(1, ge=1, le=168),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get error statistics."""
    try:
        service = get_monitoring_service(db)

        stats = await service.get_error_stats(hours)

        return {
            "status": "success",
            "stats": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Performance Tracking ─────────────────────────────────────────────────────

@router.post("/performance/record-request")
async def record_request_performance(
    endpoint: str = Query(...),
    method: str = Query(...),
    duration_ms: float = Query(...),
    status_code: int = Query(...),
    user_id: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Record API request performance."""
    try:
        service = get_monitoring_service(db)

        await service.record_request_performance(
            endpoint=endpoint,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            user_id=user_id,
        )

        return {
            "status": "success",
            "message": "Performance recorded",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/stats")
async def get_performance_stats(
    hours: int = Query(1, ge=1, le=168),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get API performance statistics."""
    try:
        service = get_monitoring_service(db)

        stats = await service.get_performance_stats(hours)

        return {
            "status": "success",
            "stats": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Alerting ─────────────────────────────────────────────────────────────────

@router.post("/alerts/create")
async def create_alert(
    title: str = Query(...),
    message: str = Query(...),
    severity: str = Query(..., description="info, warning, critical"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Create an alert."""
    try:
        service = get_monitoring_service(db)

        await service.create_alert(title, message, severity)

        return {
            "status": "success",
            "message": "Alert created",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_recent_alerts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get recent alerts."""
    try:
        service = get_monitoring_service(db)

        alerts = await service.get_recent_alerts(limit)

        return {
            "status": "success",
            "count": len(alerts),
            "alerts": alerts,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Uptime ───────────────────────────────────────────────────────────────────

@router.get("/uptime")
async def get_uptime(
    days: int = Query(7, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get system uptime percentage."""
    try:
        service = get_monitoring_service(db)

        uptime = await service.get_uptime_percentage(days)

        return {
            "status": "success",
            "period_days": days,
            "uptime_percentage": uptime,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_monitoring_dashboard(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    """Get comprehensive monitoring dashboard."""
    try:
        service = get_monitoring_service(db)

        dashboard = await service.get_monitoring_dashboard(redis_client)

        return {
            "status": "success",
            "dashboard": dashboard,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
