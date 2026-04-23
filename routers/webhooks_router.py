"""
Webhooks & Integrations API Router
Custom webhooks, Slack, email, event management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
import asyncio

from services.webhooks_integration_service import (
    WebhookIntegrationService,
    EventType,
    IntegrationPlatform,
    get_webhook_service,
)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _require_user_id(user_id: str) -> str:
    user_id = (user_id or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required.")
    return user_id


async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    from core.pipeline import get_database

    result = get_database()
    if asyncio.iscoroutinefunction(get_database):
        return await result
    return result


# ── Webhook Management ───────────────────────────────────────────────────────

@router.post("/register")
async def register_webhook(
    user_id: str,
    url: str = Query(...),
    events: List[str] = Query(..., description="Event types to subscribe to"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Register a new webhook."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        # Convert string events to EventType enums
        event_enums = [EventType(e) for e in events]

        webhook_id = await service.register_webhook(
            user_id=user_id,
            url=url,
            events=event_enums,
        )

        if not webhook_id:
            raise HTTPException(status_code=500, detail="Failed to register webhook")

        return {
            "status": "success",
            "webhook_id": webhook_id,
            "events": events,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
@router.get("/")
async def get_user_webhooks(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get all webhooks for user."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        webhooks = await service.get_user_webhooks(user_id)

        return {
            "status": "success",
            "count": len(webhooks),
            "webhooks": webhooks,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    url: str = Query(None),
    events: List[str] = Query(None),
    is_active: bool = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Update webhook configuration."""
    try:
        service = get_webhook_service(db)

        event_enums = [EventType(e) for e in events] if events else None

        success = await service.update_webhook(
            webhook_id=webhook_id,
            url=url,
            events=event_enums,
            is_active=is_active,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "status": "success",
            "message": "Webhook updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Delete a webhook."""
    try:
        service = get_webhook_service(db)

        success = await service.delete_webhook(webhook_id)

        if not success:
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {
            "status": "success",
            "message": "Webhook deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Slack Integration ────────────────────────────────────────────────────────

@router.post("/integrations/slack/setup")
async def setup_slack_integration(
    user_id: str,
    webhook_url: str = Query(...),
    channel: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Setup Slack integration."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        integration_id = await service.setup_slack_integration(
            user_id=user_id,
            webhook_url=webhook_url,
            channel=channel,
        )

        if not integration_id:
            raise HTTPException(status_code=500, detail="Failed to setup Slack integration")

        return {
            "status": "success",
            "integration_id": integration_id,
            "platform": "slack",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/slack/notify")
async def send_slack_notification(
    user_id: str,
    title: str = Query(...),
    message: str = Query(...),
    color: str = Query("#36a64f"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send notification to Slack."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        success = await service.send_slack_notification(
            user_id=user_id,
            title=title,
            message=message,
            color=color,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send Slack notification")

        return {
            "status": "success",
            "message": "Notification sent to Slack",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Email Integration ────────────────────────────────────────────────────────

@router.post("/integrations/email/setup")
async def setup_email_integration(
    user_id: str,
    email_address: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Setup email notifications."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        integration_id = await service.setup_email_integration(
            user_id=user_id,
            email_address=email_address,
        )

        if not integration_id:
            raise HTTPException(status_code=500, detail="Failed to setup email integration")

        return {
            "status": "success",
            "integration_id": integration_id,
            "platform": "email",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Delivery Tracking ────────────────────────────────────────────────────────

@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get delivery history for webhook."""
    try:
        service = get_webhook_service(db)

        deliveries = await service.get_webhook_deliveries(webhook_id, limit)

        return {
            "status": "success",
            "webhook_id": webhook_id,
            "count": len(deliveries),
            "deliveries": deliveries,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{webhook_id}/stats")
async def get_webhook_stats(
    webhook_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get delivery statistics for webhook."""
    try:
        service = get_webhook_service(db)

        stats = await service.get_delivery_stats(webhook_id)

        return {
            "status": "success",
            "webhook_id": webhook_id,
            "stats": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Integrations List ────────────────────────────────────────────────────────

@router.get("/integrations/list")
async def get_user_integrations(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Get all integrations for user."""
    try:
        user_id = _require_user_id(user_id)
        service = get_webhook_service(db)

        integrations = await service.get_user_integrations(user_id)

        return {
            "status": "success",
            "count": len(integrations),
            "integrations": integrations,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
