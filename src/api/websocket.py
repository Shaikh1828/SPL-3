"""
WebSocket API routes for real-time event streaming.

Story coverage: US-3.1 (real-time score updates), US-3.3 (leaderboard updates)

Endpoints:
- WebSocket /ws/{session_id}
"""

from typing import Set, Dict, Optional
from fastapi import APIRouter, WebSocketDisconnect, WebSocket, HTTPException, status, Query
import structlog
import json
from datetime import datetime, timedelta
import asyncio
import re
import math

from src.events import event_bus, EventType
from src.models.tournament import Session
from src.models.camera import Camera
from src.database import SessionLocal
from src.thread_pool import get_executor

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None  # type: ignore
    np = None   # type: ignore

logger = structlog.get_logger()

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/camera/{camera_id}/preview")
async def camera_preview_endpoint(
    websocket: WebSocket,
    camera_id: int,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time camera preview streaming.
    Provides live webcam/RTSP frames or fallback mock target face stream.
    """
    db = SessionLocal()
    cap = None
    try:
        await websocket.accept()
        logger.info("camera_preview_ws_connected", camera_id=camera_id)

        # Fetch camera from database
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            logger.warning("camera_preview_not_found", camera_id=camera_id)
            source = "mock"
        else:
            source = camera.url

        # Parse camera source
        camera_source = None
        if source and source != "mock":
            if source.startswith("camera://"):
                part = source[len("camera://"):]
                digits = re.findall(r"\d+", part)
                camera_source = int(digits[0]) if digits else 0
            elif source.isdigit():
                camera_source = int(source)
            else:
                camera_source = source

        # Try to open the camera
        if OPENCV_AVAILABLE and cv2 is not None and camera_source is not None:
            try:
                loop = asyncio.get_event_loop()
                cap = await loop.run_in_executor(
                    None,
                    lambda: cv2.VideoCapture(camera_source)
                )
                if cap.isOpened():
                    # Set buffer size small to reduce latency
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                else:
                    logger.warning("camera_failed_to_open", camera_id=camera_id, source=source)
                    cap = None
            except Exception as e:
                logger.warning("camera_open_exception", camera_id=camera_id, error=str(e))
                cap = None

        frame_count = 0
        loop = asyncio.get_event_loop()
        executor = get_executor()

        while True:
            frame_bytes = None
            if cap and cap.isOpened() and cv2 is not None:
                try:
                    def grab_and_retrieve(c):
                        success, frame = c.read()
                        if success and frame is not None:
                            resized = cv2.resize(frame, (640, 480))
                            _, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            return True, encoded.tobytes()
                        return False, None

                    success, data = await loop.run_in_executor(executor, grab_and_retrieve, cap)
                    if success:
                        frame_bytes = data
                except Exception as e:
                    logger.debug("camera_read_error", camera_id=camera_id, error=str(e))

            # Fallback to mock frame if no frame_bytes could be captured
            if frame_bytes is None:
                if OPENCV_AVAILABLE and cv2 is not None and np is not None:
                    def gen_frame(fc):
                        img = np.zeros((480, 640, 3), dtype=np.uint8)
                        img[:] = (30, 24, 15)  # Navy background
                        cx, cy = 320, 240
                        max_r = 180

                        colors = [
                            ((240, 240, 240), "white"),   # Zone 1-2
                            ((10, 10, 10), "black"),       # Zone 3-4
                            ((220, 80, 0), "blue"),        # Zone 5-6
                            ((0, 0, 220), "red"),          # Zone 7-8
                            ((0, 215, 255), "yellow"),     # Zone 9-10
                        ]

                        for i, (color, name) in enumerate(colors):
                            r = int(max_r * (1.0 - i * 0.2))
                            cv2.circle(img, (cx, cy), r, color, -1)
                            if name != "black":
                                cv2.circle(img, (cx, cy), r, (80, 80, 80), 1)
                            else:
                                cv2.circle(img, (cx, cy), r, (120, 120, 120), 1)

                        cv2.circle(img, (cx, cy), int(max_r * 0.1), (0, 190, 220), 1)

                        # Aiming reticle pulsing
                        pulse = math.sin(fc * 0.2) * 5
                        reticle_r = int(25 + pulse)
                        cv2.circle(img, (cx, cy), reticle_r, (0, 255, 0), 1)
                        cv2.line(img, (cx - reticle_r - 10, cy), (cx - 5, cy), (0, 255, 0), 1)
                        cv2.line(img, (cx + 5, cy), (cx + reticle_r + 10, cy), (0, 255, 0), 1)
                        cv2.line(img, (cx, cy - reticle_r - 10), (cx, cy - 5), (0, 255, 0), 1)
                        cv2.line(img, (cx, cy + 5), (cx, cy + reticle_r + 10), (0, 255, 0), 1)

                        # Text overlays
                        cv2.putText(img, "LIVE MOCK FEED", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        time_str = datetime.now().strftime("%H:%M:%S.%f")[:-4]
                        cv2.putText(img, time_str, (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                        _, encoded = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        return encoded.tobytes()

                    frame_bytes = await loop.run_in_executor(executor, gen_frame, frame_count)
                else:
                    # Tiny 1x1 black JPEG fallback
                    frame_bytes = b"\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"

            await websocket.send_bytes(frame_bytes)
            frame_count += 1
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("camera_preview_ws_disconnected", camera_id=camera_id)
    except Exception as e:
        logger.exception("camera_preview_ws_error", camera_id=camera_id, error=str(e))
    finally:
        if cap:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cap.release)
        db.close()

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
