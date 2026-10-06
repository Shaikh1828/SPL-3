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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.dependencies import get_current_user, require_roles
from src.schemas import (
    CameraCreate,
    CameraUpdate,
    CameraResponse,
    CameraAssignRequest,
    CameraAssignmentResponse,
    CameraTestRequest,
    CameraTestResponse,
    CameraDiscoveryItem,
)
from src.models.user import User
from src.models.camera import Camera, CameraLaneAssignment
from src.models.tournament import Session
from src.services.camera_service import CameraService
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(tags=["cameras"])

# Dependency shortcut for camera management
require_camera_manager = require_roles(["admin", "scorer"])


@router.get("/sessions/{session_id}/cameras", response_model=List[CameraResponse])
async def list_session_cameras(session_id: int, db: SQLSession = Depends(get_db)):
    """
    List all cameras in a session with their assigned lane number.

    Story: US-5.1
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
        assignments = (
            db.query(CameraLaneAssignment)
            .filter(CameraLaneAssignment.session_id == session_id)
            .all()
        )
        lane_map = {a.camera_id: a.lane for a in assignments}

        result = []
        for cam in cameras:
            result.append(
                CameraResponse(
                    id=cam.id,
                    name=cam.name,
                    camera_type=cam.camera_type,
                    url=cam.url,
                    status=cam.status,
                    lane=lane_map.get(cam.id),
                    last_connected_at=cam.last_connected_at,
                    created_at=cam.created_at,
                )
            )

        logger.info("session_cameras_listed", session_id=session_id, count=len(result))
        return result

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
    current_user: User = Depends(require_camera_manager),
    db: SQLSession = Depends(get_db),
):
    """
    Connect a camera to a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        camera_id: Camera ID
        current_user: Authenticated user (Requires Admin or Scorer)
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
    current_user: User = Depends(require_camera_manager),
    db: SQLSession = Depends(get_db),
):
    """
    Disconnect a camera from a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        camera_id: Camera ID
        current_user: Authenticated user (Requires Admin or Scorer)
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
    current_user: User = Depends(require_camera_manager),
    db: SQLSession = Depends(get_db),
):
    """
    Attempt to reconnect a camera with automatic retry logic.

    Story: US-5.1

    Uses Pattern #5: Camera Reconnection (exponential backoff, user notification at attempt 3).

    Args:
        camera_id: Camera ID
        current_user: Authenticated user (Requires Admin or Scorer)
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
    current_user: User = Depends(require_camera_manager),
    db: SQLSession = Depends(get_db),
):
    """
    Assign a camera to a lane in a session.

    Story: US-5.1

    Args:
        session_id: Session ID
        assign_data: Assignment details (camera_id, lane)
        current_user: Authenticated user (Requires Admin or Scorer)
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

        # Check if lane already assigned in this session - if so, update/reassign to new camera
        existing_lane_assign = (
            db.query(CameraLaneAssignment)
            .filter(
                CameraLaneAssignment.session_id == session_id,
                CameraLaneAssignment.lane == assign_data.lane,
            )
            .first()
        )

        # Check if this camera was already assigned to another lane in this session
        existing_cam_assign = (
            db.query(CameraLaneAssignment)
            .filter(
                CameraLaneAssignment.session_id == session_id,
                CameraLaneAssignment.camera_id == assign_data.camera_id,
            )
            .first()
        )

        if existing_cam_assign and existing_cam_assign.lane != assign_data.lane:
            # Reassign camera to new lane
            existing_cam_assign.lane = assign_data.lane
            if existing_lane_assign and existing_lane_assign.id != existing_cam_assign.id:
                db.delete(existing_lane_assign)
            db.commit()
            db.refresh(existing_cam_assign)
            return existing_cam_assign

        if existing_lane_assign:
            # Update the lane to point to the new camera
            existing_lane_assign.camera_id = assign_data.camera_id
            db.commit()
            db.refresh(existing_lane_assign)
            return existing_lane_assign

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
    current_user: User = Depends(require_camera_manager),
):
    """Register a new camera in the system (Requires Admin or Scorer)."""
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


@router.put("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    camera_data: CameraUpdate,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(require_camera_manager),
):
    """Update camera configuration (Name, Stream URL, Camera Type)."""
    try:
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        if camera_data.name is not None:
            camera.name = camera_data.name
        if camera_data.camera_type is not None:
            camera.camera_type = camera_data.camera_type
        if camera_data.url is not None:
            camera.url = camera_data.url

        db.commit()
        db.refresh(camera)
        logger.info("camera_updated", camera_id=camera.id, name=camera.name)
        return camera
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("update_camera_error", camera_id=camera_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update camera",
        )


@router.post("/sessions/{session_id}/quick-setup-obs", response_model=dict)
async def quick_setup_obs(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(require_camera_manager),
):
    """
    1-Click OBS Studio auto-setup.
    Discovers local video sources and OBS Virtual Cameras and assigns them to session lanes.
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        num_lanes = session.num_lanes or 6
        discovered = CameraService.discover_local_cameras()

        assigned_count = 0
        for lane_idx in range(1, num_lanes + 1):
            dev_url = f"camera://{lane_idx - 1}"
            dev_name = f"OBS Virtual Cam / Stream Lane {lane_idx}"

            # Check if camera exists
            cam = db.query(Camera).filter(Camera.url == dev_url).first()
            if not cam:
                cam = Camera(
                    name=dev_name,
                    camera_type="USB",
                    url=dev_url,
                    status="connected",
                )
                db.add(cam)
                db.commit()
                db.refresh(cam)

            # Assign to lane
            existing_assign = (
                db.query(CameraLaneAssignment)
                .filter(
                    CameraLaneAssignment.session_id == session_id,
                    CameraLaneAssignment.lane == lane_idx,
                )
                .first()
            )
            if not existing_assign:
                new_assign = CameraLaneAssignment(
                    camera_id=cam.id,
                    session_id=session_id,
                    lane=lane_idx,
                )
                db.add(new_assign)
                assigned_count += 1
            else:
                existing_assign.camera_id = cam.id

        db.commit()
        return {
            "success": True,
            "message": f"Successfully configured OBS feeds for {num_lanes} lanes ({assigned_count} newly assigned).",
            "lanes_configured": num_lanes,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("quick_setup_obs_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OBS quick setup failed: {str(e)}",
        )


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_200_OK)
async def delete_camera(
    camera_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(require_camera_manager),
):
    """Delete a camera from the system (Requires Admin or Scorer)."""
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
    current_user: User = Depends(require_camera_manager),
):
    """Unassign a camera from a session lane (Requires Admin or Scorer)."""
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


@router.get("/cameras/discover", response_model=List[CameraDiscoveryItem])
async def discover_cameras(
    current_user: User = Depends(get_current_user),
):
    """Auto-discover locally connected webcams and OBS Virtual Camera devices."""
    try:
        discovered = CameraService.discover_local_cameras()
        return [CameraDiscoveryItem(**item) for item in discovered]
    except Exception as e:
        logger.exception("discover_cameras_error", error=str(e))
        return []


@router.post("/cameras/test-stream", response_model=CameraTestResponse)
async def test_camera_stream_endpoint(
    request_data: CameraTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Test connection and live frame acquisition from any camera/OBS stream URL."""
    try:
        result = CameraService.test_camera_stream(request_data.url, request_data.camera_type)
        return CameraTestResponse(
            connected=result.get("connected", False),
            source=result.get("source", request_data.url),
            message=result.get("message", "Test completed"),
            resolution=result.get("resolution"),
            fps=result.get("fps"),
        )
    except Exception as e:
        logger.exception("test_camera_stream_error", error=str(e))
        return CameraTestResponse(
            connected=False,
            source=request_data.url,
            message=f"Test error: {str(e)}",
        )


@router.get("/cameras/{camera_id}/test", response_model=CameraTestResponse)
async def test_registered_camera(
    camera_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test connectivity and live feed of a registered camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    try:
        result = CameraService.test_camera_stream(camera.url, camera.camera_type)
        if result.get("connected"):
            camera.status = "connected"
            from datetime import datetime
            camera.last_connected_at = datetime.utcnow()
        else:
            camera.status = "disconnected"
        db.commit()
        db.refresh(camera)

        return CameraTestResponse(
            connected=result.get("connected", False),
            source=camera.url,
            message=result.get("message", "Test completed"),
            resolution=result.get("resolution"),
            fps=result.get("fps"),
        )
    except Exception as e:
        logger.exception("test_registered_camera_error", camera_id=camera_id, error=str(e))
        return CameraTestResponse(
            connected=False,
            source=camera.url,
            message=f"Test error: {str(e)}",
        )


class PushFrameBody(BaseModel):
    image_base64: str


@router.post("/cameras/{camera_id}/push-frame", status_code=status.HTTP_200_OK)
async def push_camera_frame(
    camera_id: int,
    request: Request,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(require_camera_manager),
):
    """
    Push a live video frame from the client browser / OBS bridge into backend camera memory.
    Supports application/json ({ image_base64: '...' }), multipart/form-data, or raw image bytes.
    """
    import base64
    frame_bytes = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            data = await request.json()
            b64_data = data.get("image_base64") or data.get("image") or ""
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            if b64_data:
                frame_bytes = base64.b64decode(b64_data)
        except Exception:
            pass
    elif "multipart/form-data" in content_type:
        try:
            form = await request.form()
            file_item = form.get("file")
            if file_item and hasattr(file_item, "read"):
                frame_bytes = await file_item.read()
            elif "image_base64" in form:
                b64_data = str(form["image_base64"])
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                frame_bytes = base64.b64decode(b64_data)
        except Exception:
            pass
    else:
        raw_body = await request.body()
        if raw_body:
            if raw_body.startswith(b"data:image") or b"base64" in raw_body[:30]:
                try:
                    s = raw_body.decode("utf-8")
                    if "," in s:
                        s = s.split(",", 1)[1]
                    frame_bytes = base64.b64decode(s)
                except Exception:
                    frame_bytes = raw_body
            else:
                frame_bytes = raw_body

    if not frame_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid frame provided")

    CameraService.store_pushed_frame(camera_id, frame_bytes)

    # If camera is assigned to a session lane, also store for that lane
    assign = db.query(CameraLaneAssignment).filter(CameraLaneAssignment.camera_id == camera_id).first()
    if assign:
        CameraService.store_lane_pushed_frame(assign.session_id, assign.lane, frame_bytes)

    # Mark camera as connected in database
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam and cam.status != "connected":
        cam.status = "connected"
        from datetime import datetime
        cam.last_connected_at = datetime.utcnow()
        db.commit()

    return {"success": True, "camera_id": camera_id, "size": len(frame_bytes)}


@router.post("/sessions/{session_id}/lanes/{lane}/push-frame", status_code=status.HTTP_200_OK)
async def push_lane_frame(
    session_id: int,
    lane: int,
    request: Request,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(require_camera_manager),
):
    """
    Push a live video frame directly for a session lane.
    Supports application/json ({ image_base64: '...' }), multipart/form-data, or raw image bytes.
    """
    import base64
    frame_bytes = None
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            data = await request.json()
            b64_data = data.get("image_base64") or data.get("image") or ""
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            if b64_data:
                frame_bytes = base64.b64decode(b64_data)
        except Exception:
            pass
    elif "multipart/form-data" in content_type:
        try:
            form = await request.form()
            file_item = form.get("file")
            if file_item and hasattr(file_item, "read"):
                frame_bytes = await file_item.read()
            elif "image_base64" in form:
                b64_data = str(form["image_base64"])
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                frame_bytes = base64.b64decode(b64_data)
        except Exception:
            pass
    else:
        raw_body = await request.body()
        if raw_body:
            if raw_body.startswith(b"data:image") or b"base64" in raw_body[:30]:
                try:
                    s = raw_body.decode("utf-8")
                    if "," in s:
                        s = s.split(",", 1)[1]
                    frame_bytes = base64.b64decode(s)
                except Exception:
                    frame_bytes = raw_body
            else:
                frame_bytes = raw_body

    if not frame_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid frame provided")

    CameraService.store_lane_pushed_frame(session_id, lane, frame_bytes)
    return {"success": True, "session_id": session_id, "lane": lane, "size": len(frame_bytes)}


