"""
AegisAI - Real-Time WebSocket Service
Live task progress, instant notifications, collaborative updates
Uses FastAPI WebSocket + Redis pub/sub for scalability
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import asdict, dataclass

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


@dataclass
class TaskUpdateEvent:
    """Real-time task update event."""
    task_id: str
    user_id: str
    status: str
    progress: int
    message: str
    timestamp: str


@dataclass
class NotificationEvent:
    """Real-time notification event."""
    user_id: str
    title: str
    message: str
    type: str  # 'info', 'warning', 'error', 'success'
    timestamp: str


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    Handles connection lifecycle, message routing, and Redis pub/sub.
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize WebSocket manager."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis = redis_client
        self.channels = {}

    # ── Connection Management ─────────────────────────────────────────────────

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept WebSocket connection and register user."""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

        # Subscribe to Redis channel if available
        if self.redis:
            await self._subscribe_to_channel(user_id)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove disconnected WebSocket."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Unsubscribe from Redis
                if self.redis and user_id in self.channels:
                    await self.channels[user_id].unsubscribe()
                    del self.channels[user_id]

        logger.info(f"WebSocket disconnected for user {user_id}")

    async def _subscribe_to_channel(self, user_id: str) -> None:
        """Subscribe to Redis channel for user."""
        if not self.redis:
            return

        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f"user:{user_id}:updates")
            self.channels[user_id] = pubsub

            # Listen for messages
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self.broadcast_to_user(user_id, data)

        except Exception as e:
            logger.error(f"Redis subscription error for {user_id}: {e}")

    # ── Message Broadcasting ──────────────────────────────────────────────────

    async def broadcast_to_user(
        self,
        user_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Broadcast message to all connections of a user."""
        if user_id not in self.active_connections:
            return

        disconnected = set()

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(user_id, ws)

    async def broadcast_to_all(self, data: Dict[str, Any]) -> None:
        """Broadcast message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, data)

    async def send_to_user(
        self,
        user_id: str,
        message_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Send typed message to user."""
        payload = {
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        await self.broadcast_to_user(user_id, payload)

    # ── Task Updates ──────────────────────────────────────────────────────────

    async def send_task_update(
        self,
        user_id: str,
        task_id: str,
        status: str,
        progress: int = 0,
        message: str = "",
    ) -> None:
        """
        Send task progress update in real-time.

        Status: pending, processing, completed, failed
        Progress: 0-100
        """
        event = TaskUpdateEvent(
            task_id=task_id,
            user_id=user_id,
            status=status,
            progress=progress,
            message=message,
            timestamp=datetime.now().isoformat(),
        )

        # Broadcast to user
        await self.send_to_user(user_id, "task_update", asdict(event))

        # Publish to Redis for other instances
        if self.redis:
            await self.redis.publish(
                f"user:{user_id}:updates",
                json.dumps(asdict(event))
            )

    async def send_task_started(self, user_id: str, task_id: str) -> None:
        """Notify task has started processing."""
        await self.send_task_update(
            user_id=user_id,
            task_id=task_id,
            status="processing",
            progress=10,
            message="Task started processing"
        )

    async def send_task_progress(
        self,
        user_id: str,
        task_id: str,
        progress: int,
        stage: str,
    ) -> None:
        """Send progress update during task execution."""
        await self.send_task_update(
            user_id=user_id,
            task_id=task_id,
            status="processing",
            progress=progress,
            message=f"Currently at: {stage}"
        )

    async def send_task_completed(
        self,
        user_id: str,
        task_id: str,
        results: Dict[str, Any],
    ) -> None:
        """Notify task completion."""
        await self.send_to_user(user_id, "task_completed", {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        })

    async def send_task_failed(
        self,
        user_id: str,
        task_id: str,
        error: str,
    ) -> None:
        """Notify task failure."""
        await self.send_to_user(user_id, "task_failed", {
            "task_id": task_id,
            "status": "failed",
            "error": error,
            "timestamp": datetime.now().isoformat(),
        })

    # ── Notifications ─────────────────────────────────────────────────────────

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
    ) -> None:
        """
        Send notification to user.

        Types: 'info', 'warning', 'error', 'success'
        """
        event = NotificationEvent(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            timestamp=datetime.now().isoformat(),
        )

        await self.send_to_user(user_id, "notification", asdict(event))

    async def send_success_notification(self, user_id: str, title: str, message: str) -> None:
        """Send success notification."""
        await self.send_notification(user_id, title, message, "success")

    async def send_error_notification(self, user_id: str, title: str, message: str) -> None:
        """Send error notification."""
        await self.send_notification(user_id, title, message, "error")

    async def send_warning_notification(self, user_id: str, title: str, message: str) -> None:
        """Send warning notification."""
        await self.send_notification(user_id, title, message, "warning")

    # ── Analytics Updates ─────────────────────────────────────────────────────

    async def send_analytics_update(
        self,
        user_id: str,
        kpis: Dict[str, Any],
    ) -> None:
        """Send live analytics update."""
        await self.send_to_user(user_id, "analytics_update", {
            "kpis": kpis,
            "timestamp": datetime.now().isoformat(),
        })

    # ── Connection Status ─────────────────────────────────────────────────────

    def get_active_users(self) -> List[str]:
        """Get list of currently connected users."""
        return list(self.active_connections.keys())

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for user."""
        return len(self.active_connections.get(user_id, set()))

    def is_user_online(self, user_id: str) -> bool:
        """Check if user has active WebSocket connection."""
        return user_id in self.active_connections

    def get_total_connections(self) -> int:
        """Get total active WebSocket connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    # ── Batch Operations ──────────────────────────────────────────────────────

    async def broadcast_bulk_update(
        self,
        updates: List[Dict[str, Any]],
    ) -> None:
        """Broadcast multiple updates efficiently."""
        for update in updates:
            user_id = update.get("user_id")
            if user_id:
                await self.send_to_user(user_id, "bulk_update", update)

    # ── Room/Channel Support ──────────────────────────────────────────────────

    async def join_room(self, user_id: str, room_id: str, websocket: WebSocket) -> None:
        """Join a collaborative room."""
        room_key = f"room:{room_id}"
        if room_key not in self.active_connections:
            self.active_connections[room_key] = set()
        self.active_connections[room_key].add(websocket)
        logger.info(f"User {user_id} joined room {room_id}")

    async def leave_room(self, room_id: str, websocket: WebSocket) -> None:
        """Leave a collaborative room."""
        room_key = f"room:{room_id}"
        if room_key in self.active_connections:
            self.active_connections[room_key].discard(websocket)

    async def broadcast_to_room(self, room_id: str, data: Dict[str, Any]) -> None:
        """Broadcast message to all users in a room."""
        room_key = f"room:{room_id}"
        if room_key in self.active_connections:
            for websocket in list(self.active_connections[room_key]):
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    logger.error(f"Failed to send to room {room_id}: {e}")


# ── Singleton Instance ───────────────────────────────────────────────────────

_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager(redis_client: Optional[Redis] = None) -> WebSocketManager:
    """Get or create WebSocket manager singleton."""
    global _ws_manager

    if _ws_manager is None:
        _ws_manager = WebSocketManager(redis_client)

    return _ws_manager
