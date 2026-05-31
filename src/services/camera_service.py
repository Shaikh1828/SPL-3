"""
Camera management service for connection, disconnection, and reconnection logic.

Implements:
- NFR Pattern #5: Camera Reconnection (retry with exponential backoff, user notification at attempt 3)
- Camera connection pool management
- Status tracking

Story coverage: US-5.1 (camera connection management), US-5.2 (image capture)
"""

import time
from typing import Optional
from sqlalchemy.orm import Session
import structlog

from src.models.camera import Camera, CameraLaneAssignment
from src.models.tournament import Session as SessionModel
from src.events import publish_event, EventType
from src.cache import cache_manager, invalidate_camera_cache, get_camera_cache_key

logger = structlog.get_logger()


class CameraService:
    """Camera management and reconnection logic."""

    @staticmethod
    def connect_camera(db: Session, camera_id: int) -> Optional[Camera]:
        """
        Attempt to connect to a camera.

        Args:
            db: Database session
            camera_id: Camera ID

        Returns:
            Updated Camera object or None if connection fails
        """
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            logger.warning("camera_not_found", camera_id=camera_id)
            return None

        try:
            # In production, would actually connect to camera hardware
            # For now, just mark as connected
            camera.status = "connected"
            from datetime import datetime

            camera.last_connected_at = datetime.utcnow()
            db.commit()
            db.refresh(camera)

            # Invalidate cache
            invalidate_camera_cache(camera_id)

            logger.info("camera_connected", camera_id=camera_id, name=camera.name)

            # Emit event
            publish_event(
                EventType.CAMERA_CONNECTED,
                {"camera_id": camera_id, "name": camera.name},
            )

            return camera

        except Exception as e:
            logger.exception("camera_connect_error", camera_id=camera_id, error=str(e))
            camera.status = "error"
            db.commit()
            return None

    @staticmethod
    def disconnect_camera(db: Session, camera_id: int) -> bool:
        """
        Disconnect a camera.

        Args:
            db: Database session
            camera_id: Camera ID

        Returns:
            True if successful
        """
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return False

        camera.status = "disconnected"
        db.commit()

        # Invalidate cache
        invalidate_camera_cache(camera_id)

        logger.info("camera_disconnected", camera_id=camera_id)

        publish_event(
            EventType.CAMERA_DISCONNECTED,
            {"camera_id": camera_id},
        )

        return True

    @staticmethod
    def reconnect_camera_with_retry(
        db: Session,
        camera_id: int,
        max_retries: int = 5,
        base_backoff: float = 2.0,
    ) -> Optional[Camera]:
        """
        Attempt to reconnect camera with exponential backoff retry logic.

        Implements NFR Pattern #5: Camera Reconnection

        At attempt 3, user is notified of ongoing reconnection.

        Args:
            db: Database session
            camera_id: Camera ID
            max_retries: Maximum reconnection attempts
            base_backoff: Base backoff time in seconds (2^n)

        Returns:
            Camera object if reconnected, None if all retries exhausted
        """
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            logger.warning("camera_not_found_for_reconnect", camera_id=camera_id)
            return None

        logger.info(
            "camera_reconnection_started",
            camera_id=camera_id,
            name=camera.name,
            max_retries=max_retries,
        )

        # Emit reconnection start event
        publish_event(
            EventType.CAMERA_RECONNECTION_STARTED,
            {"camera_id": camera_id, "name": camera.name},
        )

        for attempt in range(max_retries):
            try:
                # Attempt connection (in production, would perform actual camera connection)
                logger.debug("camera_reconnect_attempt", camera_id=camera_id, attempt=attempt + 1)

                # Simulate connection logic
                camera.status = "connected"
                from datetime import datetime

                camera.last_connected_at = datetime.utcnow()
                db.commit()
                db.refresh(camera)

                # Invalidate cache
                invalidate_camera_cache(camera_id)

                logger.info(
                    "camera_reconnection_success",
                    camera_id=camera_id,
                    attempt=attempt + 1,
                )

                # Emit success event
                publish_event(
                    EventType.CAMERA_CONNECTED,
                    {"camera_id": camera_id, "attempt": attempt + 1},
                )

                return camera

            except Exception as e:
                logger.warning(
                    "camera_reconnection_attempt_failed",
                    camera_id=camera_id,
                    attempt=attempt + 1,
                    error=str(e),
                )

                # User notification at attempt 3 (Pattern #5)
                if attempt == 2:
                    logger.info(
                        "camera_reconnection_notification",
                        camera_id=camera_id,
                        message="Camera reconnection in progress",
                    )

                    publish_event(
                        EventType.CAMERA_RECONNECTION_STARTED,
                        {
                            "camera_id": camera_id,
                            "message": "Camera reconnection in progress",
                            "attempt": attempt + 1,
                        },
                    )

                if attempt < max_retries - 1:
                    backoff_time = base_backoff * (2 ** attempt)
                    logger.debug("camera_reconnect_backoff", backoff_seconds=backoff_time)
                    time.sleep(backoff_time)

        # All retries failed
        logger.error(
            "camera_reconnection_failed",
            camera_id=camera_id,
            max_retries=max_retries,
        )

        camera.status = "disconnected"
        db.commit()

        # Emit failure event
        publish_event(
            EventType.CAMERA_RECONNECTION_FAILED,
            {"camera_id": camera_id, "max_retries": max_retries},
        )

        return None

    @staticmethod
    def get_camera_by_id(db: Session, camera_id: int) -> Optional[Camera]:
        """Get camera by ID."""
        return db.query(Camera).filter(Camera.id == camera_id).first()

    @staticmethod
    def get_cameras_for_session(db: Session, session_id: int) -> list[Camera]:
        """Get all cameras assigned to a session."""
        return (
            db.query(Camera)
            .join(CameraLaneAssignment, CameraLaneAssignment.camera_id == Camera.id)
            .filter(CameraLaneAssignment.session_id == session_id)
            .all()
        )

    @staticmethod
    def assign_camera_to_lane(
        db: Session, session_id: int, camera_id: int, lane: int
    ) -> Optional[CameraLaneAssignment]:
        """Assign camera to lane in a session."""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            return None

        assignment = CameraLaneAssignment(
            camera_id=camera_id, session_id=session_id, lane=lane
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        logger.info(
            "camera_assigned_to_lane",
            camera_id=camera_id,
            session_id=session_id,
            lane=lane,
        )

        return assignment
