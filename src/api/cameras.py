"""
Camera API routes.

Story coverage: US-5.1 (camera connection management), US-5.2 (image capture)

Endpoints:
- GET /sessions/{session_id}/cameras
- POST /sessions/{session_id}/cameras/{camera_id}/connect
- POST /sessions/{session_id}/cameras/{camera_id}/disconnect
- POST /cameras/{camera_id}/reconnect
- POST /sessions/{session_id}/cameras/assign
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.schemas import CameraCreate, CameraResponse, CameraAssignRequest, CameraAssignmentResponse
from src.dependencies import get_current_user
from src.models.user import User
from src.models.camera import Camera, CameraLaneAssignment
from src.models.tournament import Session
from src.services.camera_service import CameraService
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(tags=["cameras"])


@router.get("/sessions/{session_id}/cameras", response_model=List[CameraResponse])
async def list_session_cameras(session_id: int, db: SQLSession = Depends(get_db)):
    """
    List all cameras in a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        List of cameras assigned to session

    Raises:
        HTTPException: 404 if session not found
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        cameras = CameraService.get_cameras_for_session(db, session_id)
        logger.info("session_cameras_listed", session_id=session_id, count=len(cameras))
        return cameras

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_cameras_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cameras",
        )


@router.post("/sessions/{session_id}/cameras/{camera_id}/connect", response_model=CameraResponse)
async def connect_camera(
    session_id: int,
    camera_id: int,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Connect a camera to a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        camera_id: Camera ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated camera with connected status

    Raises:
        HTTPException: 404 if session or camera not found
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify camera exists
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        CameraService.connect_camera(db, camera_id)
        db.refresh(camera)

        logger.info("camera_connected", session_id=session_id, camera_id=camera_id)
        return camera

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("connect_camera_error", camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect camera",
        )


@router.post("/sessions/{session_id}/cameras/{camera_id}/disconnect", response_model=CameraResponse)
async def disconnect_camera(
    session_id: int,
    camera_id: int,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Disconnect a camera from a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        camera_id: Camera ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated camera with disconnected status

    Raises:
        HTTPException: 404 if session or camera not found
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify camera exists
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        CameraService.disconnect_camera(db, camera_id)
        db.refresh(camera)

        logger.info("camera_disconnected", session_id=session_id, camera_id=camera_id)
        return camera

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("disconnect_camera_error", camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect camera",
        )


@router.post("/cameras/{camera_id}/reconnect", response_model=dict)
async def reconnect_camera(
    camera_id: int,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Attempt to reconnect a camera with automatic retry logic.

    Story: US-5.1

    Uses Pattern #5: Camera Reconnection (exponential backoff, user notification at attempt 3).

    Args:
        camera_id: Camera ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Reconnection status dict

    Raises:
        HTTPException: 404 if camera not found
    """
    try:
        # Verify camera exists
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        CameraService.reconnect_camera_with_retry(
            db, camera_id, max_retries=5, base_backoff=2.0
        )
        db.refresh(camera)

        logger.info("camera_reconnect_initiated", camera_id=camera_id)

        return {
            "status": "reconnecting",
            "camera_id": camera_id,
            "current_status": camera.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("reconnect_camera_error", camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate camera reconnection",
        )


@router.post("/sessions/{session_id}/cameras/assign", response_model=CameraAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_camera_to_lane(
    session_id: int,
    assign_data: CameraAssignRequest,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Assign a camera to a lane in a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        assign_data: Assignment details (camera_id, lane)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created camera assignment

    Raises:
        HTTPException: 404 if session/camera not found, 400 if lane already assigned
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify camera exists
        camera = db.query(Camera).filter(Camera.id == assign_data.camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        # Check if lane already assigned
        existing = (
            db.query(CameraLaneAssignment)
            .filter(
                CameraLaneAssignment.session_id == session_id,
                CameraLaneAssignment.lane == assign_data.lane,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lane {assign_data.lane} already has a camera assigned",
            )

        assignment = CameraLaneAssignment(
            camera_id=assign_data.camera_id,
            session_id=session_id,
            lane=assign_data.lane,
        )

        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        logger.info("camera_lane_assigned", session_id=session_id, lane=assign_data.lane, camera_id=assign_data.camera_id)
        return assignment

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("assign_camera_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign camera to lane",
        )


@router.get("/cameras", response_model=List[CameraResponse])
async def list_global_cameras(
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all cameras registered in the system."""
    try:
        cameras = db.query(Camera).order_by(Camera.id.asc()).all()
        return cameras
    except Exception as e:
        logger.exception("list_global_cameras_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve global cameras",
        )


@router.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def register_camera(
    camera_data: CameraCreate,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new camera in the system."""
    try:
        # Check duplicate name
        existing = db.query(Camera).filter(Camera.name == camera_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Camera with name '{camera_data.name}' already exists",
            )

        new_camera = Camera(
            name=camera_data.name,
            camera_type=camera_data.camera_type,
            url=camera_data.url,
            status="disconnected",
        )
        db.add(new_camera)
        db.commit()
        db.refresh(new_camera)
        logger.info("camera_registered", camera_id=new_camera.id, name=new_camera.name)
        return new_camera
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("register_camera_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register camera",
        )


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_200_OK)
async def delete_camera(
    camera_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a camera from the system."""
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )
        # Remove assignments first
        db.query(CameraLaneAssignment).filter(CameraLaneAssignment.camera_id == camera_id).delete()
        
        db.delete(camera)
        db.commit()
        logger.info("camera_deleted", camera_id=camera_id)
        return {"success": True, "message": "Camera successfully deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("delete_camera_error", camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete camera",
        )


@router.delete("/sessions/{session_id}/cameras/{camera_id}", status_code=status.HTTP_200_OK)
async def unassign_camera(
    session_id: int,
    camera_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unassign a camera from a session lane."""
    try:
        assignment = (
            db.query(CameraLaneAssignment)
            .filter(CameraLaneAssignment.session_id == session_id, CameraLaneAssignment.camera_id == camera_id)
            .first()
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera assignment not found in this session",
            )
        db.delete(assignment)
        db.commit()
        logger.info("camera_unassigned", session_id=session_id, camera_id=camera_id)
        return {"success": True, "message": "Camera assignment successfully removed"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("unassign_camera_error", session_id=session_id, camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove camera assignment",
        )


@router.get("/sessions/{session_id}/assignments", response_model=List[CameraAssignmentResponse])
async def list_session_camera_assignments(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all camera assignments in a session."""
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        assignments = db.query(CameraLaneAssignment).filter(CameraLaneAssignment.session_id == session_id).order_by(CameraLaneAssignment.lane.asc()).all()
        return assignments
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_assignments_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list camera assignments",
        )
