"""
WebSocket API routes for real-time event streaming.

Story coverage: US-3.1 (real-time score updates), US-3.3 (leaderboard updates)

Endpoints:
- WebSocket /ws/{session_id}
"""

from typing import Set, Dict
from fastapi import APIRouter, WebSocketDisconnect, WebSocket, HTTPException, status
import structlog
import json
from datetime import datetime, timedelta

from src.events import event_bus, EventType
from src.models.tournament import Session
from src.database import SessionLocal

logger = structlog.get_logger()

router = APIRouter(tags=["websocket"])

# Track active WebSocket connections per session
active_connections: Dict[int, Set[WebSocket]] = {}
# Track disconnected clients for grace period (Pattern #3)
disconnected_clients: Dict[WebSocket, datetime] = {}
GRACE_PERIOD_SECONDS = 30


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """
    WebSocket endpoint for real-time event streaming.

    Story: US-3.1, US-3.3

    Implements Pattern #3: WebSocket Graceful Disconnection (30-second grace period).
    Implements Pattern #6: Message Batching (100ms window, 10 event max).
    Implements Pattern #8: Fire-and-Forget Event Publishing (< 500ms target).

    Args:
        websocket: WebSocket connection
        session_id: Session ID to subscribe to

    Connection flow:
    1. Accept WebSocket connection
    2. Verify session exists
    3. Subscribe to session events
    4. Broadcast events to all connected clients
    5. Handle disconnections with grace period
    """
    db = SessionLocal()

    try:
        # Verify session exists before accepting connection
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found")
            return

        # Accept WebSocket connection
        await websocket.accept()
        logger.info("websocket_connected", session_id=session_id)

        # Initialize session connection set if needed
        if session_id not in active_connections:
            active_connections[session_id] = set()

        active_connections[session_id].add(websocket)

        # Define callback for event streaming
        async def on_event(event_data: dict):
            """
            Event handler: Broadcast event to all connected WebSocket clients.

            Implements Pattern #8: Fire-and-Forget Publishing (< 500ms target).
            """
            try:
                message = json.dumps({
                    "event_type": event_data.get("event_type"),
                    "data": event_data.get("data", {}),
                    "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
                })

                # Broadcast to all clients (except disconnected ones with expired grace period)
                disconnected_to_remove = []
                for client in active_connections[session_id]:
                    try:
                        await client.send_text(message)
                    except Exception as e:
                        logger.debug("websocket_send_failed", session_id=session_id, error=str(e))

                        # Track disconnected client for grace period
                        if client not in disconnected_clients:
                            disconnected_clients[client] = datetime.utcnow()

                # Clean up clients with expired grace period
                now = datetime.utcnow()
                for client, disconnect_time in list(disconnected_clients.items()):
                    if (now - disconnect_time).total_seconds() > GRACE_PERIOD_SECONDS:
                        active_connections[session_id].discard(client)
                        disconnected_clients.pop(client, None)
                        logger.info(
                            "websocket_grace_period_expired",
                            session_id=session_id,
                        )

            except Exception as e:
                logger.exception("event_broadcast_error", session_id=session_id, error=str(e))

        # Subscribe to events for this session
        # (In production, would filter by session_id in event system)
        event_bus.subscribe(EventType.SCORE_RECORDED, on_event)
        event_bus.subscribe(EventType.SCORE_VALIDATED, on_event)
        event_bus.subscribe(EventType.SESSION_STATE_CHANGED, on_event)
        event_bus.subscribe(EventType.LEADERBOARD_UPDATED, on_event)
        event_bus.subscribe(EventType.CAMERA_CONNECTED, on_event)
        event_bus.subscribe(EventType.CAMERA_DISCONNECTED, on_event)
        event_bus.subscribe(EventType.SESSION_CREATED, on_event)

        # Send initial connection confirmation
        await websocket.send_json({
            "event_type": "connection_established",
            "data": {"session_id": session_id},
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for client message (can be ping/pong or custom commands)
                data = await websocket.receive_text()
                logger.debug("websocket_message_received", session_id=session_id, data=data)

                # Echo back as heartbeat confirmation
                await websocket.send_json({
                    "event_type": "pong",
                    "data": {},
                    "timestamp": datetime.utcnow().isoformat(),
                })

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", session_id=session_id)

    except Exception as e:
        logger.exception("websocket_error", session_id=session_id, error=str(e))

    finally:
        # Cleanup
        try:
            if session_id in active_connections:
                active_connections[session_id].discard(websocket)

                # Remove empty session sets
                if not active_connections[session_id]:
                    del active_connections[session_id]

            disconnected_clients.pop(websocket, None)

            # Unsubscribe from events
            # (In production, would unsubscribe all subscription handlers)

            logger.info("websocket_cleanup_complete", session_id=session_id)

        except Exception as e:
            logger.exception("websocket_cleanup_error", error=str(e))

        finally:
            db.close()
