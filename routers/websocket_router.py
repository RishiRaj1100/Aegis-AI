"""
WebSocket Router
Real-time task updates, notifications, live analytics
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

from services.websocket_service import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
):
    """
    WebSocket endpoint for real-time updates.
    
    Connection format: ws://localhost:8000/ws/{user_id}
    
    Receives events:
    - task_update: Task progress update
    - task_completed: Task finished
    - task_failed: Task error
    - notification: General notification
    - analytics_update: Live analytics
    """
    try:
        # Initialize WebSocket manager
        ws_manager = get_websocket_manager()

        # Accept connection
        await ws_manager.connect(user_id, websocket)
        logger.info(f"WebSocket connected for user {user_id}")

        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id,
            "message": "Connected to AegisAI real-time updates",
        })

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            event_type = data.get("type")
            payload = data.get("payload", {})

            # Handle different message types
            if event_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": str(__import__("datetime").datetime.now()),
                })

            elif event_type == "subscribe_task":
                task_id = payload.get("task_id")
                logger.info(f"User {user_id} subscribed to task {task_id}")

            elif event_type == "unsubscribe_task":
                task_id = payload.get("task_id")
                logger.info(f"User {user_id} unsubscribed from task {task_id}")

            else:
                logger.warning(f"Unknown message type: {event_type}")

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await ws_manager.disconnect(user_id, websocket)


@router.websocket("/room/{room_id}")
async def websocket_room_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str = Query(...),
):
    """
    WebSocket endpoint for collaborative rooms.
    
    Connection format: ws://localhost:8000/ws/room/{room_id}?user_id={user_id}
    
    Supports:
    - Collaborative task editing
    - Group notifications
    - Shared dashboards
    """
    try:
        ws_manager = get_websocket_manager()

        await websocket.accept()
        await ws_manager.join_room(user_id, room_id, websocket)
        logger.info(f"User {user_id} joined room {room_id}")

        # Notify room members
        await ws_manager.broadcast_to_room(room_id, {
            "type": "user_joined",
            "user_id": user_id,
            "message": f"User {user_id} joined the room",
        })

        while True:
            data = await websocket.receive_json()

            message_type = data.get("type")
            content = data.get("content", {})

            # Broadcast to room
            await ws_manager.broadcast_to_room(room_id, {
                "type": message_type,
                "user_id": user_id,
                "content": content,
                "timestamp": str(__import__("datetime").datetime.now()),
            })

    except WebSocketDisconnect:
        await ws_manager.leave_room(room_id, websocket)
        logger.info(f"User {user_id} left room {room_id}")

    except Exception as e:
        logger.error(f"Room WebSocket error: {e}")


# Helper functions for sending WebSocket events

async def send_task_update_ws(
    user_id: str,
    task_id: str,
    status: str,
    progress: int,
    message: str,
    redis_client = None,
):
    """Send task update via WebSocket."""
    ws_manager = get_websocket_manager(redis_client)
    await ws_manager.send_task_update(user_id, task_id, status, progress, message)


async def send_notification_ws(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    redis_client = None,
):
    """Send notification via WebSocket."""
    ws_manager = get_websocket_manager(redis_client)
    await ws_manager.send_notification(user_id, title, message, notification_type)


async def send_analytics_update_ws(
    user_id: str,
    kpis: dict,
    redis_client = None,
):
    """Send analytics update via WebSocket."""
    ws_manager = get_websocket_manager(redis_client)
    await ws_manager.send_analytics_update(user_id, kpis)


async def broadcast_to_all_ws(
    data: dict,
    redis_client = None,
):
    """Broadcast to all connected users."""
    ws_manager = get_websocket_manager(redis_client)
    await ws_manager.broadcast_to_all(data)


# Status endpoints

@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection status."""
    try:
        ws_manager = get_websocket_manager()

        return {
            "status": "success",
            "active_users": ws_manager.get_active_users(),
            "total_connections": ws_manager.get_total_connections(),
            "user_counts": {
                user_id: ws_manager.get_user_connection_count(user_id)
                for user_id in ws_manager.get_active_users()
            },
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
        }


@router.get("/user/{user_id}/status")
async def get_user_connection_status(
    user_id: str,
):
    """Check if user has active WebSocket connection."""
    try:
        ws_manager = get_websocket_manager()

        return {
            "status": "success",
            "user_id": user_id,
            "is_online": ws_manager.is_user_online(user_id),
            "connection_count": ws_manager.get_user_connection_count(user_id),
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e),
        }
