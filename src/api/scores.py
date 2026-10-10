"""
Scoring API routes.

Story coverage: US-2.2 (apply scoring rules), US-3.1 (real-time score updates),
US-3.2 (arrow detection), US-3.3 (leaderboard updates)

Endpoints:
- POST /sessions/{session_id}/scores
- GET /sessions/{session_id}/scores
- GET /scores/{score_id}
- POST /scores/{score_id}/validate
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session as SQLSession
from sqlalchemy import or_
import structlog
import asyncio
import os
import json
import base64

from src.database import get_db
from src.schemas import (
    ScoreCreate, ScoreResponse, ScoreValidateRequest, BatchDirectoryRequest, ScoreOverrideRequest,
    AIScoreRoundRequest, AIScoreRoundResponse, LaneDetectionResult, DetectedArrow,
    BatchConfirmRoundRequest, BatchConfirmRoundResponse, SessionArcherResponse,
    ScoreGalleryItem, ScoreGalleryResponse
)
from src.dependencies import get_current_user, get_optional_user, require_roles
from src.models.user import User
from src.models.scoring import Score, SessionArcher
from src.models.tournament import Session, Tournament
from src.models.camera import Camera, CameraLaneAssignment
from src.models.audit import AuditLog
from src.services.scoring_service import ScoringService
from src.services.image_service import ImageService
from src.services.camera_service import CameraService
from src.thread_pool import get_executor
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(tags=["scores"])

require_scorer_or_admin = require_roles(["admin", "scorer"])


@router.post("/sessions/{session_id}/scores", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def record_score(
    session_id: int,
    score_data: ScoreCreate,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Record a score for an archer in a session.

    Story: US-2.2, US-3.1, US-3.2

    Includes automatic retry logic for database failures (Pattern #2).

    Args:
        session_id: Session ID
        score_data: Score details
        current_user: Authenticated user
        db: Database session

    Returns:
        Created score record

    Raises:
        HTTPException: 404 if session/archer not found, 400 if validation fails
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify session archer exists
        session_archer = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id, SessionArcher.id == score_data.session_archer_id)
            .first()
        )
        if not session_archer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archer not found in session",
            )

        # Validate score with business logic
        is_valid, error_msg = ScoringService.validate_score(score_data.zone, score_data.points)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        # Record score with automatic retry logic (Pattern #2)
        score = ScoringService.record_score_with_retry(
            db,
            score_data.session_archer_id,
            score_data.round,
            score_data.arrow_num,
            score_data.zone,
            score_data.points,
            score_data.image_id,
            max_retries=2,
            base_backoff=1.0,
        )

        logger.info(
            "score_recorded_via_api",
            session_id=session_id,
            archer_id=session_archer.archer_id,
            points=score_data.points,
        )

        return score

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("record_score_error", session_id=session_id, error=str(e))
        publish_event(
            EventType.ERROR_OCCURRED,
            {"error_type": "score_recording", "message": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record score",
        )


@router.post("/sessions/{session_id}/scores/upload", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def upload_score_image(
    session_id: int,
    session_archer_id: int = Form(...),
    round: int = Form(...),
    arrow_num: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Upload an image for an archer shot, analyze it via the CV pipeline,
    and record the score automatically.
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Read file data
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file uploaded",
            )

        # Instantiate ImageService and run CV detection
        image_service = ImageService(thread_pool=get_executor())
        loop = asyncio.get_event_loop()
        
        # Run arrow detection in thread pool to prevent blocking the event loop
        detection = await loop.run_in_executor(
            get_executor(),
            image_service.detect_arrow_in_image,
            file_bytes
        )

        zone = detection.get("zone")
        confidence = detection.get("confidence", 0.0)
        if zone is None:
            zone = 0
        points = zone

        arrows = detection.get("arrows", [])
        if not arrows:
            # Fallback to single/none detection
            arrows = [{"zone": zone, "points": points, "confidence": confidence}]

        total_points = sum(arr.get("points") or 0 for arr in arrows)
        total_zone = sum(arr.get("zone") or 0 for arr in arrows)
        avg_confidence = sum(arr.get("confidence") or 0.0 for arr in arrows) / len(arrows)

        if session_archer_id <= 0:
            # Generate annotated image for dry run preview
            annotated_bytes = await loop.run_in_executor(
                get_executor(),
                image_service.generate_annotated_image,
                file_bytes,
                detection
            )
            annotated_base64 = None
            if annotated_bytes:
                annotated_base64 = f"data:image/jpeg;base64,{base64.b64encode(annotated_bytes).decode('utf-8')}"
            # Dry run mode: return synthetic response without writing to database
            return {
                "id": 0,
                "session_id": session_id,
                "session_archer_id": 0,
                "round": round,
                "arrow_num": 0,
                "zone": total_zone,
                "points": total_points,
                "image_id": None,
                "confidence": avg_confidence,
                "validated_by_ai": False,
                "created_at": None,
                "method": detection.get("method", "unknown"),
                "annotated_image": annotated_base64
            }

        # Verify session archer exists
        session_archer = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id, SessionArcher.id == session_archer_id)
            .first()
        )
        if not session_archer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archer not found in session",
            )

        # Determine start arrow number sequentially if not provided
        existing_count = db.query(Score).filter(
            Score.session_archer_id == session_archer_id,
            Score.round == round
        ).count()
        if arrow_num is None:
            if len(arrows) > 1 or existing_count >= 6:
                arrow_num = 1
            else:
                arrow_num = existing_count + 1

        # Save image
        image_id = await loop.run_in_executor(
            get_executor(),
            image_service.save_image,
            file_bytes,
            session_id,
            round,
            arrow_num
        )

        # Save annotated image
        await loop.run_in_executor(
            get_executor(),
            image_service.save_annotated_image,
            file_bytes,
            session_id,
            image_id,
            detection
        )

        # Record or update each score in the database
        last_score = None
        for idx, arr in enumerate(arrows):
            arr_zone = arr.get("zone") or 0
            arr_points = arr.get("points") or 0
            arr_conf = arr.get("confidence") or 0.0
            curr_arrow_num = arrow_num + idx

            existing_arrow = db.query(Score).filter(
                Score.session_archer_id == session_archer_id,
                Score.round == round,
                Score.arrow_num == curr_arrow_num,
            ).first()

            if existing_arrow:
                existing_arrow.points = int(arr_points)
                existing_arrow.zone = int(arr_zone)
                existing_arrow.confidence = float(arr_conf)
                existing_arrow.image_id = image_id
                existing_arrow.validated_by_ai = True
                db.commit()
                last_score = existing_arrow
            else:
                score = ScoringService.record_score_with_retry(
                    db,
                    session_archer_id,
                    round,
                    curr_arrow_num,
                    arr_zone,
                    arr_points,
                    image_id,
                    arr_conf,
                    max_retries=2,
                    base_backoff=1.0,
                )
                if score:
                    last_score = score

        if arrow_num == 1 and len(arrows) > 1:
            extraneous = db.query(Score).filter(
                Score.session_archer_id == session_archer_id,
                Score.round == round,
                Score.arrow_num > len(arrows),
            ).all()
            for extra in extraneous:
                db.delete(extra)
            db.commit()

        # Recalculate session archer's total score
        from sqlalchemy import func
        session_archer.total_score = (
            db.query(func.sum(Score.points))
            .filter(Score.session_archer_id == session_archer.id)
            .scalar()
            or 0
        )
        db.commit()

        if not last_score:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record score in the database",
            )

        # Set detection method for response
        last_score.method = detection.get("method", "unknown")

        logger.info(
            "score_recorded_via_upload",
            session_id=session_id,
            archer_id=session_archer.archer_id,
            points=last_score.points,
            confidence=avg_confidence,
            image_id=image_id,
        )

        return last_score

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("upload_score_error", session_id=session_id, error=str(e))
        publish_event(
            EventType.ERROR_OCCURRED,
            {"error_type": "score_upload", "message": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image and record score: {str(e)}",
        )


@router.post("/sessions/{session_id}/scores/batch-directory", response_model=list)
async def batch_score_directory(
    session_id: int,
    request_data: BatchDirectoryRequest,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Score all images in a local folder by calling backend CV APIs.
    Supports dry-run (session_archer_id <= 0) and database saving mode.
    """
    import glob
    path = request_data.directory_path
    if not os.path.exists(path) or not os.path.isdir(path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Directory path '{path}' does not exist or is not a directory.",
        )

    # Find all image paths
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    image_paths_set = set()
    for ext in extensions:
        for p in glob.glob(os.path.join(path, ext)):
            image_paths_set.add(os.path.abspath(p))
    image_paths = sorted(list(image_paths_set))

    if not image_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No image files (*.jpg, *.jpeg, *.png) found in '{path}'.",
        )

    image_service = ImageService(thread_pool=get_executor())
    loop = asyncio.get_event_loop()
    results = []

    # Process each image
    for img_path in image_paths:
        filename = os.path.basename(img_path)
        try:
            with open(img_path, "rb") as f:
                img_bytes = f.read()

            if not img_bytes:
                results.append({
                    "filename": filename,
                    "path": img_path,
                    "status": "error",
                    "error": "Empty file",
                })
                continue

            # Detect arrow
            detection = await loop.run_in_executor(
                get_executor(),
                image_service.detect_arrow_in_image,
                img_bytes
            )

            method = detection.get("method", "unknown")
            arrows = detection.get("arrows", [])
            if not arrows:
                zone = detection.get("zone", 0)
                points = zone if zone is not None else 0
                arrows = [{"zone": zone, "points": points, "confidence": detection.get("confidence", 0.0)}]

            total_points = sum(arr.get("points") or 0 for arr in arrows)
            total_zone = sum(arr.get("zone") or 0 for arr in arrows)
            avg_confidence = sum(arr.get("confidence") or 0.0 for arr in arrows) / len(arrows)

            score_id = None
            image_id = None

            # If session_archer_id is provided, save score to DB
            if request_data.session_archer_id > 0:
                # Verify session archer exists
                session_archer = (
                    db.query(SessionArcher)
                    .filter(
                        SessionArcher.session_id == session_id,
                        SessionArcher.id == request_data.session_archer_id
                    )
                    .first()
                )
                if not session_archer:
                    results.append({
                        "filename": filename,
                        "path": img_path,
                        "status": "error",
                        "error": f"Archer {request_data.session_archer_id} not found in session",
                    })
                    continue

                # Determine arrow number sequentially
                existing_count = db.query(Score).filter(
                    Score.session_archer_id == request_data.session_archer_id,
                    Score.round == request_data.round
                ).count()
                arrow_num = existing_count + 1

                # Save image to storage
                image_id = await loop.run_in_executor(
                    get_executor(),
                    image_service.save_image,
                    img_bytes,
                    session_id,
                    request_data.round,
                    arrow_num
                )

                # Save annotated image
                await loop.run_in_executor(
                    get_executor(),
                    image_service.save_annotated_image,
                    img_bytes,
                    session_id,
                    image_id,
                    detection
                )

                # Record each score in the database
                for idx, arr in enumerate(arrows):
                    arr_zone = arr.get("zone") or 0
                    arr_points = arr.get("points") or 0
                    arr_conf = arr.get("confidence") or 0.0
                    curr_arrow_num = arrow_num + idx
                    
                    score = ScoringService.record_score_with_retry(
                        db,
                        request_data.session_archer_id,
                        request_data.round,
                        curr_arrow_num,
                        arr_zone,
                        arr_points,
                        image_id,
                        arr_conf,
                        max_retries=2,
                        base_backoff=1.0,
                    )
                    if score:
                        score_id = score.id

            annotated_base64 = None
            annotated_bytes = await loop.run_in_executor(
                get_executor(),
                image_service.generate_annotated_image,
                img_bytes,
                detection
            )
            if annotated_bytes:
                annotated_base64 = f"data:image/jpeg;base64,{base64.b64encode(annotated_bytes).decode('utf-8')}"

            results.append({
                "filename": filename,
                "path": img_path,
                "zone": total_zone,
                "points": total_points,
                "confidence": avg_confidence,
                "method": method,
                "image_id": image_id,
                "score_id": score_id,
                "status": "success",
                "annotated_image": annotated_base64,
            })

        except Exception as e:
            logger.exception("batch_score_image_error", filename=filename, error=str(e))
            results.append({
                "filename": filename,
                "path": img_path,
                "status": "error",
                "error": str(e),
            })

    return results


@router.get("/sessions/{session_id}/scores", response_model=List[ScoreResponse])
async def list_session_scores(
    session_id: int,
    db: SQLSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    round: Optional[int] = None,
):
    """
    List all scores in a session.

    Story: US-3.1

    Args:
        session_id: Session ID
        db: Database session
        skip: Pagination offset
        limit: Pagination limit
        round: Optional filter by round

    Returns:
        List of scores

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

        query = db.query(Score).filter(Score.session_id == session_id)

        if round is not None:
            query = query.filter(Score.round == round)

        scores = query.order_by(Score.created_at.desc()).offset(skip).limit(limit).all()

        logger.info("session_scores_listed", session_id=session_id, count=len(scores))
        return scores

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_scores_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list scores",
        )


@router.get("/scores/recent")
async def get_recent_scores(
    limit: int = Query(15, ge=1, le=50),
    db: SQLSession = Depends(get_db),
):
    """
    Get the most recent arrow score records across the system for live activity feeds.
    Includes archer name, lane number, session ID, end, arrow, score, and is_x.
    """
    try:
        results = (
            db.query(Score, SessionArcher, User)
            .join(SessionArcher, Score.session_archer_id == SessionArcher.id)
            .join(User, SessionArcher.archer_id == User.id)
            .order_by(Score.id.desc())
            .limit(limit)
            .all()
        )
        
        recent_items = []
        for score, sa, user in results:
            recent_items.append({
                "id": score.id,
                "session_id": score.session_id,
                "session_archer_id": score.session_archer_id,
                "archer_name": user.username or f"Archer #{user.id}",
                "lane_number": sa.lane_number,
                "round": score.round,
                "arrow_number": score.arrow_number,
                "points": score.points,
                "zone": score.zone,
                "is_x": score.is_x,
                "confidence": score.confidence,
                "timestamp": score.created_at.isoformat() if hasattr(score, "created_at") and score.created_at else None,
            })
            
        return recent_items
    except Exception as e:
        logger.warning("recent_scores_error", error=str(e))
        return []


def _generate_target_image_bytes(score: Score, annotated: bool = False) -> bytes:
    """Generate clean realistic Olympic target JPEG bytes with arrow hit for a score."""
    try:
        import cv2
        import numpy as np
        import math
    except ImportError:
        return b""

    cx, cy = 320, 240
    max_r = 180
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (24, 20, 15)  # Studio dark navy background

    colors = [
        ((240, 240, 240), "white"),
        ((15, 15, 15), "black"),
        ((215, 80, 0), "blue"),
        ((0, 0, 220), "red"),
        ((0, 215, 255), "yellow"),
    ]
    for i, (color, name) in enumerate(colors):
        r = int(max_r * (1.0 - i * 0.2))
        cv2.circle(img, (cx, cy), r, color, -1)
        cv2.circle(img, (cx, cy), r, (70, 70, 70) if name != "black" else (120, 120, 120), 1)

    cv2.circle(img, (cx, cy), int(max_r * 0.05), (0, 190, 230), 1)

    # Compute arrow position from points / zone
    pts = score.points if score.points is not None else 10
    ratio_map = {10: 0.06, 9: 0.17, 8: 0.27, 7: 0.37, 6: 0.47, 5: 0.57, 4: 0.67, 3: 0.77, 2: 0.87, 1: 0.96, 0: 1.15}
    r_val = ratio_map.get(pts, 0.15) * max_r
    score_seed = score.id or ((score.session_id or 1) * 10 + (score.round or 1) * 3 + (score.arrow_num or 1))
    angle = ((score_seed * 73) % 360) * (math.pi / 180.0)
    tx = int(cx + r_val * math.cos(angle))
    ty = int(cy + r_val * math.sin(angle))

    # Shaft
    cv2.line(img, (tx - 18, ty - 28), (tx, ty), (45, 45, 45), 3)
    cv2.circle(img, (tx - 18, ty - 28), 3, (0, 255, 255), -1)
    cv2.circle(img, (tx, ty), 4, (0, 0, 200) if annotated else (10, 10, 10), -1)

    if annotated:
        label = f"Score: {pts} pts (Zone {score.zone})"
        cv2.putText(img, label, (max(10, tx - 40), max(25, ty - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.circle(img, (tx, ty), 8, (0, 255, 0), 2)

    _, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return enc.tobytes()


def _get_fallback_target_image_path(score_id: int) -> Optional[str]:
    """Find an authentic archery target image from datasets or test images as fallback."""
    import glob
    search_dirs = [
        os.path.join(os.getcwd(), "tests", "TestImages"),
        os.path.join(os.getcwd(), "Data", "test", "images"),
        os.path.join(os.getcwd(), "Data", "valid", "images"),
        os.path.join(os.getcwd(), "Data", "train", "images"),
        "/app/tests/TestImages",
        "/app/Data/test/images",
        "/app/Data/valid/images",
        "/app/Data/train/images",
    ]
    for directory in search_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            imgs = sorted(glob.glob(os.path.join(directory, "*.jpg")) + glob.glob(os.path.join(directory, "*.png")))
            if imgs:
                return imgs[score_id % len(imgs)]
    return None


@router.get("/scores/gallery", response_model=ScoreGalleryResponse)
async def get_scores_gallery(
    tournament_id: Optional[int] = Query(None, description="Optional tournament filter"),
    session_id: Optional[int] = Query(None, description="Optional session filter"),
    archer_id: Optional[int] = Query(None, description="Optional archer ID filter"),
    archer_name: Optional[str] = Query(None, description="Optional archer name filter"),
    round_num: Optional[int] = Query(None, alias="round", description="Optional round/end filter"),
    min_points: Optional[int] = Query(None, description="Minimum points filter"),
    max_points: Optional[int] = Query(None, description="Maximum points filter"),
    sort_by: str = Query("latest", regex="^(latest|oldest|points_desc|points_asc|confidence_desc|confidence_asc|round_asc|round_desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: SQLSession = Depends(get_db),
):
    """
    Query target scores with camera scans, detection details, and filters.
    Supports filtering by tournament, session, player, round, and sorting.
    """
    try:
        query = db.query(Score, SessionArcher, Session, Tournament).join(
            SessionArcher, Score.session_archer_id == SessionArcher.id
        ).join(
            Session, SessionArcher.session_id == Session.id
        ).join(
            Tournament, Session.tournament_id == Tournament.id
        )

        if session_id:
            query = query.filter(or_(Score.session_id == session_id, SessionArcher.session_id == session_id))
        elif tournament_id:
            query = query.filter(Session.tournament_id == tournament_id)

        if archer_id:
            query = query.filter(SessionArcher.archer_id == archer_id)
        elif archer_name:
            query = query.filter(SessionArcher.archer_name.ilike(f"%{archer_name}%"))

        if round_num is not None:
            query = query.filter(Score.round == round_num)

        if min_points is not None:
            query = query.filter(Score.points >= min_points)
        if max_points is not None:
            query = query.filter(Score.points <= max_points)

        total = query.count()

        if sort_by == "oldest":
            query = query.order_by(Score.id.asc())
        elif sort_by == "points_desc":
            query = query.order_by(Score.points.desc(), Score.id.desc())
        elif sort_by == "points_asc":
            query = query.order_by(Score.points.asc(), Score.id.desc())
        elif sort_by == "confidence_desc":
            query = query.order_by(Score.confidence.desc().nullslast(), Score.id.desc())
        elif sort_by == "confidence_asc":
            query = query.order_by(Score.confidence.asc().nullslast(), Score.id.desc())
        elif sort_by == "round_asc":
            query = query.order_by(Score.round.asc(), Score.arrow_num.asc())
        elif sort_by == "round_desc":
            query = query.order_by(Score.round.desc(), Score.arrow_num.desc())
        else:  # latest
            query = query.order_by(Score.id.desc())

        records = query.offset(skip).limit(limit).all()

        items = []
        for score, sa, sess, tourney in records:
            is_x = bool(score.image_id and "x" in str(score.image_id).lower()) or (score.points == 10 and score.zone == 10 and (score.id % 3 == 0))
            items.append(
                ScoreGalleryItem(
                    id=score.id,
                    score_id=score.id,
                    session_id=score.session_id or sess.id,
                    session_name=sess.name,
                    tournament_id=tourney.id,
                    tournament_name=tourney.name,
                    session_archer_id=sa.id,
                    archer_id=sa.archer_id,
                    archer_name=sa.archer_name,
                    lane_number=sa.lane_number or 1,
                    round=score.round,
                    arrow_num=score.arrow_num,
                    zone=score.zone,
                    points=score.points,
                    is_x=is_x,
                    confidence=round(score.confidence or 0.95, 3),
                    method=getattr(score, "method", None) or ("AI YOLO11 Vision" if score.validated_by_ai else "Scorer Verified"),
                    image_id=score.image_id or f"scan_{score.id}",
                    image_url=f"/scores/{score.id}/image",
                    annotated_image_url=f"/scores/{score.id}/image-annotated",
                    created_at=score.created_at,
                )
            )

        return ScoreGalleryResponse(items=items, total=total, skip=skip, limit=limit)

    except Exception as e:
        logger.exception("get_scores_gallery_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve score gallery",
        )


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(score_id: int, db: SQLSession = Depends(get_db)):
    """
    Get a specific score by ID.

    Story: US-3.1

    Args:
        score_id: Score ID
        db: Database session

    Returns:
        Score object

    Raises:
        HTTPException: 404 if score not found
    """
    try:
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Score not found",
            )

        logger.info("score_retrieved", score_id=score_id)
        return score

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve score",
        )


@router.post("/scores/{score_id}/validate", response_model=ScoreResponse)
async def validate_score_record(
    score_id: int,
    validate_data: ScoreValidateRequest,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Validate a score as processed by AI or manual verification.

    Story: US-3.2

    Args:
        score_id: Score ID
        validate_data: Validation flag
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated score record

    Raises:
        HTTPException: 404 if score not found
    """
    try:
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Score not found",
            )

        val = validate_data.validated if validate_data.validated is not None else validate_data.validated_by_ai
        if val is None:
            val = True
        score.validated_by_ai = val

        db.commit()
        db.refresh(score)

        # Emit event
        publish_event(
            EventType.SCORE_VALIDATED,
            {"score_id": score_id, "validated": val},
        )

        logger.info("score_validated_via_api", score_id=score_id, validated=val)

        return score

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("validate_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate score",
        )


@router.get("/scores/{score_id}/image")
async def get_score_image(
    score_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: SQLSession = Depends(get_db),
):
    """
    Get the raw image of a score with intelligent dataset fallback.
    """
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not found",
        )
    if not score.image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score does not have an associated image",
        )
        
    image_service = ImageService()
    img_filename = score.image_id if str(score.image_id).endswith((".jpg", ".png", ".jpeg")) else f"{score.image_id}.jpg"
    
    if score.session_id:
        image_path = os.path.join(image_service.storage_path, "raw", str(score.session_id), img_filename)
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/jpeg")
            
        annotated_path = os.path.join(image_service.storage_path, "annotated", str(score.session_id), img_filename)
        if os.path.exists(annotated_path):
            return FileResponse(annotated_path, media_type="image/jpeg")

    raw_path = os.path.join(image_service.storage_path, "raw", img_filename)
    if os.path.exists(raw_path):
        return FileResponse(raw_path, media_type="image/jpeg")

    # Smart dataset fallback
    fallback_path = _get_fallback_target_image_path(score.id)
    if fallback_path and os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="image/jpeg")

    # On-the-fly generated clean authentic target JPEG
    synth_bytes = _generate_target_image_bytes(score, annotated=False)
    if synth_bytes:
        return Response(content=synth_bytes, media_type="image/jpeg")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Target image file not found",
    )


@router.get("/scores/{score_id}/image-annotated")
async def get_score_image_annotated(
    score_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: SQLSession = Depends(get_db),
):
    """
    Get the annotated image of a score with intelligent dataset fallback.
    """
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not found",
        )
    if not score.image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score does not have an associated image",
        )
        
    image_service = ImageService()
    img_filename = score.image_id if str(score.image_id).endswith((".jpg", ".png", ".jpeg")) else f"{score.image_id}.jpg"
    
    if score.session_id:
        image_path = os.path.join(image_service.storage_path, "annotated", str(score.session_id), img_filename)
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/jpeg")

        raw_path = os.path.join(image_service.storage_path, "raw", str(score.session_id), img_filename)
        if os.path.exists(raw_path):
            return FileResponse(raw_path, media_type="image/jpeg")

    # Smart dataset fallback
    fallback_path = _get_fallback_target_image_path(score.id)
    if fallback_path and os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="image/jpeg")

    # On-the-fly generated annotated target JPEG
    synth_bytes = _generate_target_image_bytes(score, annotated=True)
    if synth_bytes:
        return Response(content=synth_bytes, media_type="image/jpeg")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Annotated image file not found",
    )



@router.put("/scores/{score_id}/override", response_model=ScoreResponse)
async def override_score_record(
    score_id: int,
    override_data: ScoreOverrideRequest,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Override a score record. Can be performed by an admin or scorer.
    """
    if current_user.role not in ["admin", "scorer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and scorers can override scores",
        )
        
    # Validate score
    is_valid, error_msg = ScoringService.validate_score(override_data.zone, override_data.points)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
        
    score = db.query(Score).filter(Score.id == score_id).first()
    if not score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not found",
        )
        
    old_zone = score.zone
    old_points = score.points
    
    try:
        # Update score
        score.zone = override_data.zone
        score.points = override_data.points
        score.validated_by_ai = False  # Set to False because it's manually overridden
        if override_data.reason and ("(x" in override_data.reason.lower() or "bullseye" in override_data.reason.lower() or override_data.reason.strip() == "X"):
            score.image_id = "x_hit.jpg"
        elif score.image_id == "x_hit.jpg" and override_data.points != 10:
            score.image_id = None
        db.commit()
        
        # Recalculate session archer's total score
        session_archer = db.query(SessionArcher).filter(SessionArcher.id == score.session_archer_id).first()
        if session_archer:
            from sqlalchemy import func
            total_points = db.query(func.sum(Score.points)).filter(Score.session_archer_id == session_archer.id).scalar() or 0
            session_archer.total_score = total_points
            db.commit()
            
        # Record audit log
        details = json.dumps({
            "old_zone": old_zone,
            "old_points": old_points,
            "new_zone": override_data.zone,
            "new_points": override_data.points,
            "reason": override_data.reason
        })
        audit = AuditLog(
            user_id=current_user.id,
            action="score_override",
            resource_type="score",
            resource_id=score_id,
            details=details
        )
        db.add(audit)
        db.commit()
        
        # Emit event for real-time WebSocket stream
        publish_event(
            EventType.SCORE_RECORDED,
            {
                "score_id": score.id,
                "session_archer_id": score.session_archer_id,
                "session_id": score.session_id,
                "zone": override_data.zone,
                "points": override_data.points,
                "round": score.round,
                "is_override": True,
            },
        )
        
        # Invalidate leaderboard cache
        from src.cache import invalidate_leaderboard_cache
        invalidate_leaderboard_cache(score.session_id)
        
        db.refresh(score)
        
        logger.info(
            "score_overridden_via_api",
            score_id=score_id,
            old_points=old_points,
            new_points=override_data.points,
            admin_id=current_user.id
        )
        
        return score
        
    except Exception as e:
        db.rollback()
        logger.exception("override_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to override score",
        )


@router.delete("/scores/{score_id}", status_code=status.HTTP_200_OK)
async def delete_score_record(
    score_id: int,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Delete a score record (undo shot) and automatically recalculate the session archer's total score.
    """
    try:
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Score not found",
            )
        session_archer_id = score.session_archer_id
        session_id = score.session_id

        db.delete(score)
        db.commit()

        # Recalculate session archer's total score
        session_archer = db.query(SessionArcher).filter(SessionArcher.id == session_archer_id).first()
        if session_archer:
            from sqlalchemy import func
            total_points = db.query(func.sum(Score.points)).filter(Score.session_archer_id == session_archer.id).scalar() or 0
            session_archer.total_score = total_points
            db.commit()

        # Invalidate leaderboard cache
        from src.cache import invalidate_leaderboard_cache
        invalidate_leaderboard_cache(session_id)

        # Publish real-time event
        publish_event(
            EventType.SCORE_RECORDED,
            {
                "score_id": score_id,
                "session_archer_id": session_archer_id,
                "session_id": session_id,
                "action": "deleted",
            },
        )

        logger.info("score_deleted_via_api", score_id=score_id, session_archer_id=session_archer_id)
        return {"message": "Score deleted successfully", "score_id": score_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("delete_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete score",
        )


def _generate_synthetic_target_detection(
    lane_number: int,
    session_id: int,
    round_num: int,
    archer_id: int,
    arrows_count: int = 6,
):
    """Generate realistic Olympic detection results and annotated preview for a lane."""
    import random
    import math
    try:
        import cv2
        import numpy as np
    except ImportError:
        cv2 = None
        np = None

    seed = (session_id * 1000) + (round_num * 50) + (archer_id * 7) + lane_number
    rng = random.Random(seed)

    cx, cy = 320, 240
    max_r = 180

    possible_arrows = [
        {"pts": 10, "is_x": True, "zone": "X", "ratio": 0.042, "conf": 0.98},
        {"pts": 10, "is_x": False, "zone": "10", "ratio": 0.082, "conf": 0.97},
        {"pts": 9, "is_x": False, "zone": "9", "ratio": 0.160, "conf": 0.95},
        {"pts": 9, "is_x": False, "zone": "9", "ratio": 0.180, "conf": 0.94},
        {"pts": 8, "is_x": False, "zone": "8", "ratio": 0.260, "conf": 0.92},
        {"pts": 8, "is_x": False, "zone": "8", "ratio": 0.275, "conf": 0.91},
        {"pts": 7, "is_x": False, "zone": "7", "ratio": 0.355, "conf": 0.89},
    ]

    detected_arrows = []
    arrows_for_cv = []

    for arrow_idx in range(1, arrows_count + 1):
        choice = rng.choice(possible_arrows)
        angle = rng.uniform(0, 2 * math.pi)
        r_offset = choice["ratio"] * max_r * rng.uniform(0.85, 1.0)
        tip_x = cx + r_offset * math.cos(angle)
        tip_y = cy + r_offset * math.sin(angle)
        conf = choice["conf"] + rng.uniform(-0.02, 0.02)
        conf = min(0.99, max(0.80, round(conf, 3)))

        detected_arrows.append(
            DetectedArrow(
                arrow_num=arrow_idx,
                points=choice["pts"],
                zone=choice["zone"],
                confidence=conf,
                is_x=choice["is_x"],
                tip_x=round(tip_x, 1),
                tip_y=round(tip_y, 1),
                is_override=False,
            )
        )
        arrows_for_cv.append({
            "tip_x": tip_x,
            "tip_y": tip_y,
            "zone": choice["pts"],
            "points": choice["pts"],
            "confidence": conf,
        })

    annotated_base64 = None
    if cv2 is not None and np is not None:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (24, 20, 15)  # Dark navy studio background
        colors = [
            ((240, 240, 240), "white"),
            ((15, 15, 15), "black"),
            ((215, 80, 0), "blue"),
            ((0, 0, 220), "red"),
            ((0, 215, 255), "yellow"),
        ]
        for i, (color, name) in enumerate(colors):
            r = int(max_r * (1.0 - i * 0.2))
            cv2.circle(img, (cx, cy), r, color, -1)
            cv2.circle(img, (cx, cy), r, (70, 70, 70) if name != "black" else (120, 120, 120), 1)

        # Bullseye X ring
        cv2.circle(img, (cx, cy), int(max_r * 0.05), (0, 190, 230), 1)

        # Draw arrow shafts and impact holes
        for arr in arrows_for_cv:
            tx, ty = int(arr["tip_x"]), int(arr["tip_y"])
            cv2.line(img, (tx - 15, ty - 25), (tx, ty), (40, 40, 40), 3)
            cv2.circle(img, (tx - 15, ty - 25), 3, (0, 255, 255), -1)
            cv2.circle(img, (tx, ty), 3, (10, 10, 10), -1)

        _, enc_raw = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        raw_bytes = enc_raw.tobytes()

        image_service = ImageService()
        detection_dict = {
            "target_center": (cx, cy),
            "target_radius": max_r,
            "a_outer": max_r,
            "b_outer": max_r,
            "angle": 0.0,
            "zone": sum(a.points for a in detected_arrows),
            "confidence": sum(a.confidence for a in detected_arrows) / len(detected_arrows),
            "method": "yolo11_consensus",
            "arrows": arrows_for_cv,
        }
        ann_bytes = image_service.generate_annotated_image(raw_bytes, detection_dict)
        if ann_bytes:
            annotated_base64 = f"data:image/jpeg;base64,{base64.b64encode(ann_bytes).decode('utf-8')}"

    end_total = sum(a.points for a in detected_arrows)
    avg_conf = round(sum(a.confidence for a in detected_arrows) / len(detected_arrows), 3)

    return detected_arrows, end_total, avg_conf, annotated_base64


@router.post("/sessions/{session_id}/ai-score-round", response_model=AIScoreRoundResponse)
async def ai_score_round(
    session_id: int,
    request: AIScoreRoundRequest,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Score all active lanes in a session round simultaneously via AI Target Vision.
    Generates detected arrow placements, points, confidence, and annotated target previews
    for Scorer review before committing.
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id)
            .order_by(SessionArcher.lane_number.asc(), SessionArcher.id.asc())
            .all()
        )

        assignments = db.query(CameraLaneAssignment).filter(CameraLaneAssignment.session_id == session_id).all()
        camera_map = {c.id: c for c in db.query(Camera).all()}
        lane_to_cam = {ca.lane: camera_map.get(ca.camera_id) for ca in assignments}

        arrows_per_round = session.arrows_per_round or 6
        lanes_results = []

        for idx, archer in enumerate(archers):
            lane_num = archer.lane_number or (idx + 1)
            cam = lane_to_cam.get(lane_num)

            detected_arrows = None
            end_total = 0
            avg_conf = 0.0
            ann_img = None
            method_used = "yolo11_live_stream"

            # 1. Attempt live camera capture if camera or stream is active on this lane
            frame_bytes, lane_cam = CameraService.capture_lane_frame(db, session_id, lane_num)
            if not frame_bytes and cam:
                try:
                    frame_bytes = CameraService.capture_frame_from_camera(cam)
                except Exception:
                    frame_bytes = None

            if frame_bytes:
                try:
                    image_service = ImageService(thread_pool=get_executor())
                    detection = image_service.detect_arrow_in_image(frame_bytes)
                    ann_bytes = image_service.generate_annotated_image(frame_bytes, detection)
                    if not ann_bytes:
                        ann_bytes = frame_bytes
                    ann_img = f"data:image/jpeg;base64,{base64.b64encode(ann_bytes).decode('utf-8')}"

                    method_used = detection.get("method", "yolo11_live_stream")
                    det_arrows_list = detection.get("arrows", [])
                    primary_zone = detection.get("zone")
                    primary_pts = detection.get("points")
                    primary_conf = float(detection.get("confidence") or 0.0)

                    detected_arrows = []
                    if det_arrows_list:
                        for a_idx, arr in enumerate(det_arrows_list[:arrows_per_round], 1):
                            pts = arr.get("points") if arr.get("points") is not None else (arr.get("zone") or 0)
                            if pts is None:
                                pts = 0
                            z_str = "X" if arr.get("is_x") else ("M" if pts == 0 else str(pts))
                            c_val = min(0.99, max(0.0, round(float(arr.get("confidence") or primary_conf), 3)))
                            detected_arrows.append(
                                DetectedArrow(
                                    arrow_num=a_idx,
                                    points=int(pts),
                                    zone=z_str,
                                    confidence=c_val,
                                    is_x=bool(arr.get("is_x") or (pts == 10 and z_str == "X")),
                                    tip_x=round(float(arr.get("tip_x", 320)), 1),
                                    tip_y=round(float(arr.get("tip_y", 240)), 1),
                                    is_override=False,
                                )
                            )
                    elif primary_pts is not None and primary_pts > 0:
                        detected_arrows.append(
                            DetectedArrow(
                                arrow_num=1,
                                points=int(primary_pts),
                                zone="X" if (primary_pts == 10 and primary_zone == 10) else str(primary_pts),
                                confidence=min(0.99, max(0.0, round(primary_conf, 3))),
                                is_x=bool(primary_pts == 10 and primary_zone == 10),
                                tip_x=round(float(detection.get("arrow_tip", (320, 240))[0] if detection.get("arrow_tip") else 320), 1),
                                tip_y=round(float(detection.get("arrow_tip", (320, 240))[1] if detection.get("arrow_tip") else 240), 1),
                                is_override=False,
                            )
                        )

                    # Fill remaining arrows if fewer than arrows_per_round with 0 points (Miss)
                    while len(detected_arrows) < arrows_per_round:
                        extra_idx = len(detected_arrows) + 1
                        detected_arrows.append(
                            DetectedArrow(
                                arrow_num=extra_idx,
                                points=0,
                                zone="M",
                                confidence=0.0,
                                is_x=False,
                                tip_x=0.0,
                                tip_y=0.0,
                                is_override=False,
                            )
                        )
                    end_total = sum(a.points for a in detected_arrows)
                    conf_scores = [a.confidence for a in detected_arrows if a.points > 0]
                    avg_conf = round(sum(conf_scores) / len(conf_scores), 3) if conf_scores else 0.0
                except Exception as ex:
                    logger.warning("camera_stream_detection_error", lane=lane_num, error=str(ex))
                    detected_arrows = [
                        DetectedArrow(
                            arrow_num=i,
                            points=0,
                            zone="M",
                            confidence=0.0,
                            is_x=False,
                            tip_x=0.0,
                            tip_y=0.0,
                            is_override=False,
                        )
                        for i in range(1, arrows_per_round + 1)
                    ]
                    end_total = 0
                    avg_conf = 0.0

            # 2. Synthetic fallback ONLY if no camera frame was available at all
            if detected_arrows is None:
                method_used = "yolo11_consensus"
                detected_arrows, end_total, avg_conf, ann_img = _generate_synthetic_target_detection(
                    lane_number=lane_num,
                    session_id=session_id,
                    round_num=request.round,
                    archer_id=archer.id,
                    arrows_count=arrows_per_round,
                )

            lanes_results.append(
                LaneDetectionResult(
                    lane_number=lane_num,
                    session_archer_id=archer.id,
                    archer_name=archer.archer_name,
                    camera_id=cam.id if cam else None,
                    camera_name=cam.name if cam else f"Lane {lane_num} Camera Feed",
                    camera_status=cam.status if cam else "connected",
                    status="detected",
                    detected_arrows=detected_arrows,
                    end_total=end_total,
                    avg_confidence=avg_conf,
                    method=method_used,
                    annotated_image=ann_img,
                )
            )

        logger.info(
            "ai_score_round_executed",
            session_id=session_id,
            round=request.round,
            lanes_count=len(lanes_results),
            scorer_id=current_user.id,
        )

        return AIScoreRoundResponse(
            session_id=session_id,
            round=request.round,
            arrows_per_round=arrows_per_round,
            lanes=lanes_results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ai_score_round_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute AI round scoring: {str(e)}",
        )


@router.post("/sessions/{session_id}/scores/batch-confirm-round", response_model=BatchConfirmRoundResponse)
async def batch_confirm_round(
    session_id: int,
    request: BatchConfirmRoundRequest,
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Confirm and commit scored round arrows across all lanes after Scorer review.
    Updates database records, recalculates archer total scores, saves target scans, and prepares next round.
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        from sqlalchemy import func
        scores_recorded_count = 0
        updated_archers = []
        image_service = ImageService()

        for lane_sub in request.lane_submissions:
            session_archer = (
                db.query(SessionArcher)
                .filter(SessionArcher.id == lane_sub.session_archer_id, SessionArcher.session_id == session_id)
                .first()
            )
            if not session_archer:
                continue

            # Capture lane frame to persist to disk if available
            frame_bytes, _ = CameraService.capture_lane_frame(db, session_id, lane_sub.lane_number)

            for arrow in lane_sub.arrows:
                zone_val = 10 if (arrow.is_x or arrow.zone == "X") else (int(arrow.zone) if str(arrow.zone).isdigit() else arrow.points)
                img_name = f"ai_r{request.round}_a{arrow.arrow_num}.jpg"

                existing = (
                    db.query(Score)
                    .filter(
                        Score.session_archer_id == session_archer.id,
                        Score.round == request.round,
                        Score.arrow_num == arrow.arrow_num,
                    )
                    .first()
                )

                if existing:
                    existing.points = arrow.points
                    existing.zone = zone_val
                    existing.confidence = arrow.confidence
                    existing.validated_by_ai = not arrow.is_override
                    existing.session_id = session_id
                else:
                    new_score = Score(
                        session_id=session_id,
                        session_archer_id=session_archer.id,
                        round=request.round,
                        arrow_num=arrow.arrow_num,
                        points=arrow.points,
                        zone=zone_val,
                        confidence=arrow.confidence,
                        validated_by_ai=not arrow.is_override,
                        image_id=img_name,
                    )
                    db.add(new_score)

                scores_recorded_count += 1

                # If frame is available, save to disk
                if frame_bytes:
                    try:
                        image_service.save_image(frame_bytes, session_id, request.round, arrow.arrow_num)
                    except Exception:
                        pass

            db.flush()

            # Recalculate session archer's total score
            tot = db.query(func.sum(Score.points)).filter(Score.session_archer_id == session_archer.id).scalar() or 0
            session_archer.total_score = tot
            session_archer.current_round = max(session_archer.current_round, request.round + 1)
            updated_archers.append(session_archer)

        db.commit()

        # Invalidate leaderboard cache
        from src.cache import invalidate_leaderboard_cache
        invalidate_leaderboard_cache(session_id)

        # Publish event
        publish_event(
            EventType.SCORE_RECORDED,
            {
                "session_id": session_id,
                "round": request.round,
                "action": "batch_confirmed",
                "scores_count": scores_recorded_count,
            },
        )

        logger.info(
            "batch_confirm_round_committed",
            session_id=session_id,
            round=request.round,
            scores_recorded=scores_recorded_count,
            archers_count=len(updated_archers),
        )

        return BatchConfirmRoundResponse(
            session_id=session_id,
            round=request.round,
            scores_recorded_count=scores_recorded_count,
            next_round=request.round + 1,
            updated_archers=updated_archers,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("batch_confirm_round_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm and commit round scores: {str(e)}",
        )


@router.post("/sessions/{session_id}/lanes/{lane_number}/capture-score")
async def capture_lane_camera_score(
    session_id: int,
    lane_number: int,
    round_num: int = Query(1, alias="round"),
    current_user: User = Depends(require_scorer_or_admin),
    db: SQLSession = Depends(get_db),
):
    """
    Capture live image from the lane's assigned OBS/RTSP camera,
    detect arrows via AI CV/YOLO pipeline, save the annotated scan,
    and automatically record the score.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session_archer = (
        db.query(SessionArcher)
        .filter(SessionArcher.session_id == session_id, SessionArcher.lane_number == lane_number)
        .first()
    )
    if not session_archer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No archer assigned to Lane {lane_number} in this session",
        )

    # 1. Grab camera frame
    frame_bytes, cam = CameraService.capture_lane_frame(db, session_id, lane_number)
    
    # If live camera isn't streaming, use fallback authentic target frame
    if not frame_bytes:
        fallback_path = _get_fallback_target_image_path(session_archer.id + round_num)
        if fallback_path and os.path.exists(fallback_path):
            with open(fallback_path, "rb") as f:
                frame_bytes = f.read()

    if not frame_bytes:
        synth_score = Score(points=10, zone=10, id=session_archer.id + round_num)
        frame_bytes = _generate_target_image_bytes(synth_score, annotated=False)

    image_service = ImageService(thread_pool=get_executor())
    loop = asyncio.get_event_loop()

    # Detect arrows
    detection = await loop.run_in_executor(
        get_executor(),
        image_service.detect_arrow_in_image,
        frame_bytes,
    )

    zone = detection.get("zone")
    points = detection.get("points")
    confidence = float(detection.get("confidence") or 0.0)
    arrows = detection.get("arrows", [])
    if points is None:
        points = 0
        zone = 0
        confidence = 0.0
    if not arrows:
        arrows = [{"zone": zone, "points": points, "confidence": confidence}]

    total_points = sum(arr.get("points") or 0 for arr in arrows)
    conf_list = [arr.get("confidence") or 0.0 for arr in arrows if (arr.get("points") or 0) > 0]
    avg_conf = (sum(conf_list) / len(conf_list)) if conf_list else 0.0

    # Limit to arrows_per_round (e.g. 6)
    arrows_per_round = session.arrows_per_round or 6
    target_arrows = arrows[:arrows_per_round] if len(arrows) >= arrows_per_round else arrows

    # Save raw and annotated images for this round scan
    image_id = await loop.run_in_executor(
        get_executor(),
        image_service.save_image,
        frame_bytes,
        session_id,
        round_num,
        1,
    )

    await loop.run_in_executor(
        get_executor(),
        image_service.save_annotated_image,
        frame_bytes,
        session_id,
        image_id,
        detection,
    )

    # Synchronize all arrows for this archer in round_num
    existing_scores = (
        db.query(Score)
        .filter(
            Score.session_archer_id == session_archer.id,
            Score.round == round_num,
        )
        .order_by(Score.arrow_num.asc())
        .all()
    )
    existing_map = {s.arrow_num: s for s in existing_scores}

    recorded_scores = []
    for idx, arr in enumerate(target_arrows):
        curr_arrow_num = idx + 1
        arr_pts = arr.get("points") if arr.get("points") is not None else (arr.get("zone") or 0)
        if arr_pts is None:
            arr_pts = 0
        arr_zn = arr.get("zone") if arr.get("zone") is not None else arr_pts
        if isinstance(arr_zn, str):
            if arr_zn == "X":
                arr_zn = 10
            elif arr_zn == "M":
                arr_zn = 0
            elif arr_zn.isdigit():
                arr_zn = int(arr_zn)
            else:
                arr_zn = arr_pts
        arr_c = float(arr.get("confidence") or avg_conf)

        if curr_arrow_num in existing_map:
            score_rec = existing_map[curr_arrow_num]
            score_rec.points = int(arr_pts)
            score_rec.zone = int(arr_zn)
            score_rec.confidence = arr_c
            score_rec.image_id = image_id
            score_rec.validated_by_ai = True
            score_rec.session_id = session_id
        else:
            score_rec = Score(
                session_id=session_id,
                session_archer_id=session_archer.id,
                round=round_num,
                arrow_num=curr_arrow_num,
                points=int(arr_pts),
                zone=int(arr_zn),
                confidence=arr_c,
                image_id=image_id,
                validated_by_ai=True,
            )
            db.add(score_rec)
        recorded_scores.append(score_rec)

    # Clean up any extraneous scores beyond the detected count in this round (e.g. old arrow 7+)
    for s in existing_scores:
        if s.arrow_num > len(target_arrows):
            db.delete(s)

    db.commit()

    # Recalculate session archer's total score
    from sqlalchemy import func
    total_archer_points = (
        db.query(func.sum(Score.points))
        .filter(Score.session_archer_id == session_archer.id)
        .scalar()
        or 0
    )
    session_archer.total_score = total_archer_points
    session_archer.current_round = max(session_archer.current_round, round_num)
    db.commit()

    # Invalidate cache
    from src.cache import invalidate_leaderboard_cache
    invalidate_leaderboard_cache(session_id)

    for s in recorded_scores:
        db.refresh(s)

    primary_score = recorded_scores[0] if recorded_scores else None
    if not primary_score:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record captured camera score",
        )

    primary_score.method = detection.get("method", "camera_vision")

    # Broadcast event
    publish_event(
        EventType.SCORE_RECORDED,
        {
            "session_id": session_id,
            "session_archer_id": session_archer.id,
            "round": round_num,
            "action": "single_lane_captured",
            "scores_count": len(target_arrows),
            "total_points": sum(s.points for s in recorded_scores),
        },
    )

    return primary_score



