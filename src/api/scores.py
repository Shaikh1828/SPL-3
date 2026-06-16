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
from sqlalchemy.orm import Session as SQLSession
import structlog
import asyncio
import os

from src.database import get_db
from src.schemas import ScoreCreate, ScoreResponse, ScoreValidateRequest, BatchDirectoryRequest
from src.dependencies import get_current_user
from src.models.user import User
from src.models.scoring import Score, SessionArcher
from src.models.tournament import Session
from src.services.scoring_service import ScoringService
from src.services.image_service import ImageService
from src.thread_pool import get_executor
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(tags=["scores"])


@router.post("/sessions/{session_id}/scores", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def record_score(
    session_id: int,
    score_data: ScoreCreate,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
        
        # Fallback zone if detection returned None
        if zone is None:
            zone = 0
        points = zone

        if session_archer_id <= 0:
            # Dry run mode: return synthetic response without writing to database
            return {
                "id": 0,
                "session_id": session_id,
                "session_archer_id": 0,
                "round": round,
                "arrow_num": 0,
                "zone": zone,
                "points": points,
                "image_id": None,
                "confidence": confidence,
                "validated_by_ai": False,
                "created_at": None,
                "method": detection.get("method", "unknown")
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

        # Determine arrow number sequentially if not provided
        if arrow_num is None:
            existing_count = db.query(Score).filter(
                Score.session_archer_id == session_archer_id,
                Score.round == round
            ).count()
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

        # Record score in the database
        score = ScoringService.record_score_with_retry(
            db,
            session_archer_id,
            round,
            arrow_num,
            zone,
            points,
            image_id,
            confidence,
            max_retries=2,
            base_backoff=1.0,
        )

        if not score:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record score in the database",
            )

        score.method = detection.get("method", "unknown")

        logger.info(
            "score_recorded_via_upload",
            session_id=session_id,
            archer_id=session_archer.archer_id,
            points=points,
            confidence=confidence,
            image_id=image_id,
        )

        return score

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
    current_user: User = Depends(get_current_user),
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

            zone = detection.get("zone")
            confidence = detection.get("confidence", 0.0)
            method = detection.get("method", "unknown")

            if zone is None:
                zone = 0
            points = zone

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

                # Record score in the database
                score = ScoringService.record_score_with_retry(
                    db,
                    request_data.session_archer_id,
                    request_data.round,
                    arrow_num,
                    zone,
                    points,
                    image_id,
                    confidence,
                    max_retries=2,
                    base_backoff=1.0,
                )
                if score:
                    score_id = score.id

            results.append({
                "filename": filename,
                "path": img_path,
                "zone": zone,
                "points": points,
                "confidence": confidence,
                "method": method,
                "image_id": image_id,
                "score_id": score_id,
                "status": "success",
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
