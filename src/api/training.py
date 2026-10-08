"""
API endpoints for YOLO automatic model training and monitoring.

Endpoints:
- GET /training/status: Live training status, metrics, and progress
- GET /training/dataset: Available dataset statistics (images, classes, splits)
- GET /training/history: Historical epoch metrics from results.csv
- POST /training/start: Initiate automatic training with available dataset
- POST /training/stop: Abort running training process
- POST /training/reload: Reload best.pt weights into live scoring engine
- GET /training/artifacts/{filename}: Serve training artifacts (confusion matrix, results plot)
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import structlog

from src.dependencies import get_optional_user, require_roles
from src.models.user import User
from src.schemas import (
    TrainingStartRequest,
    DatasetInfo,
    TrainingStatusResponse,
    TrainingHistoryResponse,
)
from src.services.training_service import training_service

logger = structlog.get_logger()

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/status", response_model=TrainingStatusResponse)
async def get_training_status(
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get current model training status, progress, loss, and metrics.
    """
    try:
        return training_service.get_status()
    except Exception as e:
        logger.exception("get_training_status_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch training status: {str(e)}",
        )


@router.get("/dataset", response_model=DatasetInfo)
async def get_dataset_info(
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get available dataset info (sample counts in train/valid/test, classes).
    """
    try:
        return training_service.get_dataset_info()
    except Exception as e:
        logger.exception("get_dataset_info_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dataset info: {str(e)}",
        )


@router.get("/history", response_model=TrainingHistoryResponse)
async def get_training_history(
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get epoch progression history parsed from results.csv.
    """
    try:
        return training_service.get_history()
    except Exception as e:
        logger.exception("get_training_history_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch training history: {str(e)}",
        )


@router.post("/start", response_model=TrainingStatusResponse)
async def start_training(
    payload: TrainingStartRequest = TrainingStartRequest(),
    current_user: User = Depends(require_roles(["admin", "scorer"])),
):
    """
    Start automatic training on the available archery dataset.
    Requires admin or scorer role.
    """
    try:
        training_service.start_training(
            epochs=payload.epochs,
            batch_size=payload.batch_size,
            imgsz=payload.imgsz,
            device=payload.device,
            resume=payload.resume,
        )
        return training_service.get_status()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("start_training_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training: {str(e)}",
        )


@router.post("/stop", response_model=TrainingStatusResponse)
async def stop_training(
    current_user: User = Depends(require_roles(["admin", "scorer"])),
):
    """
    Stop the currently running training pipeline.
    Requires admin or scorer role.
    """
    try:
        training_service.stop_training()
        return training_service.get_status()
    except Exception as e:
        logger.exception("stop_training_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop training: {str(e)}",
        )


@router.post("/reload")
async def reload_model(
    current_user: User = Depends(require_roles(["admin", "scorer"])),
):
    """
    Hot-reload newly trained best.pt weights into live scoring service.
    Requires admin or scorer role.
    """
    try:
        res = training_service.reload_active_model()
        return res
    except Exception as e:
        logger.exception("reload_model_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload model: {str(e)}",
        )


@router.get("/artifacts/{filename}")
async def get_training_artifact(
    filename: str,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Serve training artifact images such as results.png or confusion_matrix.png.
    """
    allowed_filenames = {
        "results.png",
        "confusion_matrix.png",
        "confusion_matrix_normalized.png",
        "BoxF1_curve.png",
        "BoxPR_curve.png",
        "BoxP_curve.png",
        "BoxR_curve.png",
        "val_batch0_labels.jpg",
        "val_batch0_pred.jpg",
        "val_batch1_labels.jpg",
        "val_batch1_pred.jpg",
        "train_batch0.jpg",
        "train_batch1.jpg",
    }
    if filename not in allowed_filenames:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found or not permitted",
        )

    file_path = os.path.join(training_service.target_run_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {filename} does not exist yet.",
        )

    media_type = "image/png" if filename.endswith(".png") else "image/jpeg"
    return FileResponse(file_path, media_type=media_type)
