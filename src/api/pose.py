"""
Pose Biomechanics & Score Prediction API Router.
Provides endpoints for benchmark video streaming, pose analysis, and ML score prediction.
"""

import os
import shutil
import tempfile
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from src.services.pose_analysis_service import PoseAnalysisService
from src.services.pose_score_model import PoseScoreModel

router = APIRouter(prefix="/pose", tags=["pose-analysis"])

pose_service = PoseAnalysisService()
score_model = PoseScoreModel()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit

class MetricPredictRequest(BaseModel):
    bow_arm_angle: float = Field(default=179.0, ge=120.0, le=200.0, description="Angle of front bow arm in degrees")
    draw_elbow_angle: float = Field(default=138.0, ge=90.0, le=180.0, description="Angle of rear drawing elbow in degrees")
    anchor_jitter: float = Field(default=0.8, ge=0.0, le=30.0, description="Anchor point positional tremor in pixels")
    bow_arm_deflection_deg: float = Field(default=0.5, ge=0.0, le=30.0, description="Downward bow arm deflection at release")
    anchor_duration_sec: float = Field(default=1.9, ge=0.2, le=10.0, description="Duration in anchor aiming phase")
    release_velocity_px: float = Field(default=32.0, ge=5.0, le=100.0, description="Rearward expansion velocity")
    torso_tilt_deg: float = Field(default=90.0, ge=70.0, le=110.0, description="Torso vertical inclination angle")


@router.get("/sample-videos")
async def list_sample_videos():
    """List all available benchmark sample archery videos."""
    videos = pose_service.list_sample_videos()
    return {"videos": videos, "total": len(videos)}


@router.get("/sample-videos/{video_id}")
async def get_sample_video_details(video_id: str):
    """Retrieve details for a specific benchmark sample video."""
    videos = pose_service.list_sample_videos()
    match = next((v for v in videos if v["id"] == video_id), None)
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample video '{video_id}' not found")
    return match


@router.get("/sample-videos/{video_id}/stream")
async def stream_sample_video(video_id: str, request: Request, range: Optional[str] = Header(None)):
    """Stream video binary data with HTTP 206 Partial Content Range support for browser scrubbing."""
    video_path = pose_service.get_sample_video_path(video_id)
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video file for '{video_id}' not found on server")

    file_size = os.path.getsize(video_path)
    
    # Handle range requests
    if range:
        try:
            range_header = range.replace("bytes=", "").split("-")
            start = int(range_header[0])
            end = int(range_header[1]) if range_header[1] else file_size - 1
            end = min(end, file_size - 1)
            content_length = (end - start) + 1

            def range_generator():
                with open(video_path, "rb") as f:
                    f.seek(start)
                    bytes_remaining = content_length
                    while bytes_remaining > 0:
                        chunk_size = min(64 * 1024, bytes_remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        bytes_remaining -= len(data)
                        yield data

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": "video/mp4",
            }
            return StreamingResponse(range_generator(), status_code=206, headers=headers)
        except Exception:
            pass  # Fall through to full response if range header invalid

    # Full content response
    def file_generator():
        with open(video_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4"
    }
    return StreamingResponse(file_generator(), headers=headers)


@router.post("/sample-videos/{video_id}/analyze")
async def analyze_sample_video(video_id: str):
    """Analyze one of the benchmark sample videos using its high-fidelity metadata."""
    try:
        result = pose_service.analyze_sample_video(video_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze-video")
async def analyze_uploaded_video(
    file: UploadFile = File(...),
    video_id: Optional[str] = Form(None)
):
    """
    Upload and analyze any archer shooting video.
    Extracts frame landmarks, segments shot phases, computes biomechanical angles,
    and returns ML predicted score (1-10 / X) and coaching diagnostics.
    """
    filename = file.filename or "upload.mp4"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format '{ext}'. Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Save to temporary file
    temp_dir = tempfile.mkdtemp(prefix="archer_pose_")
    temp_path = os.path.join(temp_dir, f"video{ext}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video file exceeds maximum size limit of {MAX_FILE_SIZE // (1024*1024)}MB."
            )

        # Run video analysis pipeline
        result = pose_service.analyze_custom_video(temp_path, video_id=video_id or filename)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error analyzing video: {str(e)}")
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


@router.post("/predict-metrics")
async def predict_from_metrics(request: MetricPredictRequest):
    """
    Direct ML model inference on manual or custom biomechanical feature vector.
    Returns Olympic ring score (1-10 / X), execution percentage, and diagnostic tips.
    """
    features = request.model_dump()
    prediction = score_model.predict(features)
    return {
        "success": True,
        "input_features": features,
        "prediction": prediction
    }


class PostureEvaluationRequest(BaseModel):
    bow_arm_angle: float = Field(default=179.0, ge=120.0, le=200.0)
    draw_elbow_angle: float = Field(default=138.0, ge=90.0, le=180.0)
    anchor_jitter: float = Field(default=0.8, ge=0.0, le=30.0)
    bow_arm_deflection_deg: float = Field(default=0.5, ge=0.0, le=30.0)
    anchor_duration_sec: float = Field(default=1.9, ge=0.2, le=10.0)
    camera_source: Optional[str] = Field(default="archer_posture_cam", description="Source camera identifier")


@router.post("/evaluate-posture")
async def evaluate_archer_posture(request: PostureEvaluationRequest):
    """
    Real-time posture accuracy evaluator for the dedicated Archer Posture Camera.
    Computes overall accuracy percentage (0-100%), component scores, and form classification.
    """
    features = request.model_dump()
    prediction = score_model.predict(features)
    accuracy = prediction.get("posture_accuracy", {})
    return {
        "success": True,
        "camera_source": request.camera_source,
        "overall_accuracy_pct": accuracy.get("overall_accuracy_pct", 90.0),
        "accuracy_tier": accuracy.get("accuracy_tier", "COMPETITIVE"),
        "accuracy_label": accuracy.get("accuracy_label", "High Competitive Form"),
        "tier_color": accuracy.get("tier_color", "#10B981"),
        "components": accuracy.get("components", {}),
        "diagnostics": prediction.get("diagnostics", []),
        "predicted_score": prediction.get("predicted_score"),
        "score_display": prediction.get("score_display")
    }

