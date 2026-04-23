"""
AegisAI - Webhooks & Integrations Service
Slack, email, external APIs, event-driven integrations, webhook management
"""

from __future__ import annotations

import logging
import json
import aiohttp
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types that trigger webhooks."""
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    ANALYTICS_UPDATED = "analytics.updated"
    RECOMMENDATION_GENERATED = "recommendation.generated"
    MILESTONE_REACHED = "milestone.reached"
    ALERT_TRIGGERED = "alert.triggered"


class IntegrationPlatform(str, Enum):
    """Supported integration platforms."""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    ZAPIER = "zapier"
    TEAMS = "teams"


class WebhookIntegrationService:
    """
    Webhooks and external integrations.

    Features:
    - Custom webhooks
    - Slack integration
    - Email notifications
    - Zapier integration
    - Event subscriptions
    - Retry logic
    - Delivery tracking
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize with MongoDB."""
        self.db = db
        self.webhooks_collection = db["webhooks"]
        self.integrations_collection = db["integrations"]
        self.webhook_deliveries_collection = db["webhook_deliveries"]
        self.event_handlers: Dict[EventType, List[Callable]] = {}

    # ── Webhook Management ────────────────────────────────────────────────────

    async def register_webhook(
        self,
        user_id: str,
        url: str,
        events: List[EventType],
        secret: Optional[str] = None,
    ) -> Optional[str]:
        """
        Register a new webhook.

        Webhooks receive POST requests with event data.
        """
        try:
            import secrets as sec

            webhook_id = f"wh_{sec.token_hex(12)}"
            webhook_secret = secret or sec.token_urlsafe(32)

            webhook = {
                "webhook_id": webhook_id,
                "user_id": user_id,
                "url": url,
                "events": [e.value for e in events],
                "secret": webhook_secret,
                "created_at": datetime.now(),
                "is_active": True,
                "delivery_count": 0,
                "failure_count": 0,
            }

            await self.webhooks_collection.insert_one(webhook)

            logger.info(f"Webhook registered for user {user_id}: {webhook_id}")
            return webhook_id

        except Exception as e:
            logger.error(f"Error registering webhook: {e}")
            return None

    async def update_webhook(
        self,
        webhook_id: str,
        events: Optional[List[EventType]] = None,
        url: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update webhook configuration."""
        try:
            updates = {}

            if events:
                updates["events"] = [e.value for e in events]

            if url:
                updates["url"] = url

            if is_active is not None:
                updates["is_active"] = is_active

            updates["updated_at"] = datetime.now()

            result = await self.webhooks_collection.update_one(
                {"webhook_id": webhook_id},
                {"$set": updates}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating webhook: {e}")
            return False

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook."""
        try:
            result = await self.webhooks_collection.delete_one({
                "webhook_id": webhook_id
            })

            return result.deleted_count > 0

        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False

    async def get_user_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all webhooks for user."""
        try:
            webhooks = await self.webhooks_collection.find({
                "user_id": user_id
            }).to_list(None)

            return webhooks

        except Exception as e:
            logger.error(f"Error getting webhooks: {e}")
            return []

    # ── Event Triggering ──────────────────────────────────────────────────────

    async def trigger_event(
        self,
        user_id: str,
        event_type: EventType,
        event_data: Dict[str, Any],
    ) -> None:
        """
        Trigger an event which sends to all registered webhooks.

        Sends to all matching webhooks asynchronously.
        """
        try:
            # Get matching webhooks
            webhooks = await self.webhooks_collection.find({
                "user_id": user_id,
                "events": event_type.value,
                "is_active": True,
            }).to_list(None)

            # Send to each webhook
            for webhook in webhooks:
                await self._deliver_webhook(webhook, event_type, event_data)

            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(user_id, event_data)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")

        except Exception as e:
            logger.error(f"Error triggering event: {e}")

    async def _deliver_webhook(
        self,
        webhook: Dict[str, Any],
        event_type: EventType,
        event_data: Dict[str, Any],
    ) -> None:
        """Deliver webhook with retry logic."""
        try:
            import hmac
            import hashlib

            payload = {
                "event": event_type.value,
                "timestamp": datetime.now().isoformat(),
                "data": event_data,
            }

            # Generate HMAC signature
            payload_str = json.dumps(payload)
            signature = hmac.new(
                webhook["secret"].encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-ID": webhook["webhook_id"],
            }

            # Attempt delivery with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            webhook["url"],
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as response:
                            if response.status == 200:
                                # Success
                                await self.webhook_deliveries_collection.insert_one({
                                    "webhook_id": webhook["webhook_id"],
                                    "event": event_type.value,
                                    "status": "success",
                                    "http_status": response.status,
                                    "timestamp": datetime.now(),
                                })

                                # Update webhook stats
                                await self.webhooks_collection.update_one(
                                    {"webhook_id": webhook["webhook_id"]},
                                    {
                                        "$inc": {"delivery_count": 1},
                                        "$set": {"last_delivery": datetime.now()}
                                    }
                                )

                                return

                except Exception as e:
                    logger.warning(f"Webhook delivery attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Final failure
                        await self.webhook_deliveries_collection.insert_one({
                            "webhook_id": webhook["webhook_id"],
                            "event": event_type.value,
                            "status": "failed",
                            "error": str(e),
                            "timestamp": datetime.now(),
                        })

                        # Update webhook stats
                        await self.webhooks_collection.update_one(
                            {"webhook_id": webhook["webhook_id"]},
                            {"$inc": {"failure_count": 1}}
                        )

        except Exception as e:
            logger.error(f"Error delivering webhook: {e}")

    # ── Slack Integration ─────────────────────────────────────────────────────

    async def setup_slack_integration(
        self,
        user_id: str,
        webhook_url: str,
        channel: str,
    ) -> Optional[str]:
        """
        Setup Slack integration.

        Requires Slack webhook URL.
        """
        try:
            integration_id = f"slack_{user_id}_{datetime.now().timestamp()}"

            integration = {
                "integration_id": integration_id,
                "user_id": user_id,
                "platform": IntegrationPlatform.SLACK.value,
                "webhook_url": webhook_url,
                "channel": channel,
                "created_at": datetime.now(),
                "is_active": True,
            }

            await self.integrations_collection.insert_one(integration)

            logger.info(f"Slack integration setup for user {user_id}")
            return integration_id

        except Exception as e:
            logger.error(f"Error setting up Slack integration: {e}")
            return None

    async def send_slack_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        color: str = "#36a64f",
    ) -> bool:
        """Send notification to Slack."""
        try:
            integration = await self.integrations_collection.find_one({
                "user_id": user_id,
                "platform": IntegrationPlatform.SLACK.value,
                "is_active": True,
            })

            if not integration:
                logger.warning(f"No active Slack integration for user {user_id}")
                return False

            payload = {
                "attachments": [{
                    "color": color,
                    "title": title,
                    "text": message,
                    "ts": int(datetime.now().timestamp()),
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    integration["webhook_url"],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    # ── Email Integration ─────────────────────────────────────────────────────

    async def setup_email_integration(
        self,
        user_id: str,
        email_address: str,
    ) -> Optional[str]:
        """Setup email notifications."""
        try:
            integration_id = f"email_{user_id}_{datetime.now().timestamp()}"

            integration = {
                "integration_id": integration_id,
                "user_id": user_id,
                "platform": IntegrationPlatform.EMAIL.value,
                "email_address": email_address,
                "created_at": datetime.now(),
                "is_active": True,
            }

            await self.integrations_collection.insert_one(integration)

            logger.info(f"Email integration setup for user {user_id}")
            return integration_id

        except Exception as e:
            logger.error(f"Error setting up email integration: {e}")
            return None

    # ── Event Subscription ────────────────────────────────────────────────────

    def subscribe_to_event(
        self,
        event_type: EventType,
        handler: Callable,
    ) -> None:
        """Subscribe to event with custom handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        logger.info(f"Handler subscribed to event: {event_type.value}")

    # ── Delivery Tracking ─────────────────────────────────────────────────────

    async def get_webhook_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get delivery history for webhook."""
        try:
            deliveries = await self.webhook_deliveries_collection.find({
                "webhook_id": webhook_id
            }).sort("timestamp", -1).to_list(limit)

            return deliveries

        except Exception as e:
            logger.error(f"Error getting deliveries: {e}")
            return []

    async def get_delivery_stats(self, webhook_id: str) -> Dict[str, Any]:
        """Get delivery statistics for webhook."""
        try:
            webhook = await self.webhooks_collection.find_one({
                "webhook_id": webhook_id
            })

            if not webhook:
                return {}

            successful = await self.webhook_deliveries_collection.count_documents({
                "webhook_id": webhook_id,
                "status": "success",
            })

            failed = await self.webhook_deliveries_collection.count_documents({
                "webhook_id": webhook_id,
                "status": "failed",
            })

            total = successful + failed

            return {
                "total_deliveries": total,
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / total * 100) if total > 0 else 0,
                "last_delivery": webhook.get("last_delivery"),
            }

        except Exception as e:
            logger.error(f"Error getting delivery stats: {e}")
            return {}

    # ── Integration Management ────────────────────────────────────────────────

    async def get_user_integrations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all integrations for user."""
        try:
            integrations = await self.integrations_collection.find({
                "user_id": user_id
            }).to_list(None)

            return integrations

        except Exception as e:
            logger.error(f"Error getting integrations: {e}")
            return []

    async def disable_integration(self, integration_id: str) -> bool:
        """Disable an integration."""
        try:
            result = await self.integrations_collection.update_one(
                {"integration_id": integration_id},
                {"$set": {"is_active": False}}
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error disabling integration: {e}")
            return False


def get_webhook_service(db: AsyncIOMotorDatabase) -> WebhookIntegrationService:
    """Get webhook service instance."""
    return WebhookIntegrationService(db)
