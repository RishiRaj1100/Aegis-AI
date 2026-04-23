"""
AegisAI - Analytics Router
GET /analytics – Retrieve aggregated statistics across all processed goals
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from routers.auth import get_current_user, require_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _get_pipeline():
    """Get the AegisAI pipeline."""
    from main import get_pipeline
    return get_pipeline()


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Get system analytics",
    description=(
        "Returns aggregated statistics across all processed goals, including "
        "average trust scores, success rates, domain distribution, and ethics flags."
    ),
)
async def get_analytics(
    current_user: Dict[str, Any] = Depends(get_current_user),
    pipeline=Depends(_get_pipeline),
) -> Dict[str, Any]:
    """
    Retrieve aggregated analytics data for dashboard visualization.

    Returns statistics about all processed goals including confidence metrics,
    success rates, and domain/ethics information.
    """
    user_id = require_current_user_id(current_user)
    # Fetch all tasks from MongoDB
    tasks = await pipeline.memory.mongo.list_tasks(limit=1000, skip=0, user_id=user_id)

    if not tasks:
        return {
            "total_goals": 0,
            "avg_trust_score": 0.0,
            "success_rate": 0.0,
            "trust_trend": [],
            "domain_distribution": {},
            "ethics_flags_by_type": {
                "privacy": 0,
                "bias": 0,
                "legal": 0,
                "other": 0,
            },
            "ethics_flags_this_week": 0,
        }

    # Calculate statistics
    total_goals = len(tasks)
    confidence_scores = [float(t.get("confidence", 0)) for t in tasks]
    avg_trust_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    # Success rate (COUNT completed or successful outcomes)
    completed_tasks = [t for t in tasks if t.get("status") == "COMPLETED"]
    success_rate = len(completed_tasks) / total_goals if total_goals > 0 else 0.0

    # Extract domains from task metadata (if available)
    domains = {}
    for task in tasks:
        # Assume domain is stored in some metadata field; adjust as needed
        domain = task.get("domain", "general")
        domains[domain] = domains.get(domain, 0) + 1

    # Ethics flags aggregation
    ethics_flags = {
        "privacy": 0,
        "bias": 0,
        "legal": 0,
        "other": 0,
    }
    ethics_this_week = 0

    # Count ethics flags if stored in tasks
    for task in tasks:
        # Check if task has ethics_scan or similar field
        ethics_scan = task.get("ethics_scan", {})
        if isinstance(ethics_scan, dict):
            if ethics_scan.get("privacy_concerns"):
                ethics_flags["privacy"] += 1
            if ethics_scan.get("bias_concerns"):
                ethics_flags["bias"] += 1
            if ethics_scan.get("legal_concerns"):
                ethics_flags["legal"] += 1
            if ethics_scan.get("flagged"):
                ethics_this_week += 1

    # Build trust trend (simple: group by date if available)
    trust_trend = []
    for task in tasks[-30:]:  # Last 30 tasks
        created_at = task.get("created_at", "")
        confidence = float(task.get("confidence", 0))
        trust_trend.append({
            "date": str(created_at)[:10],  # ISO date
            "score": round(confidence, 2),
        })

    # Risk distribution
    risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for task in tasks:
        risk_level = task.get("risk_level", "MEDIUM")
        if risk_level in risk_distribution:
            risk_distribution[risk_level] += 1

    return {
        "total_goals": total_goals,
        "avg_trust_score": round(avg_trust_score, 2),
        "success_rate": round(success_rate, 4),
        "completed_tasks": len(completed_tasks),
        "trust_trend": trust_trend,
        "domain_distribution": domains,
        "risk_distribution": risk_distribution,
        "ethics_flags_by_type": ethics_flags,
        "ethics_flags_this_week": ethics_this_week,
    }
