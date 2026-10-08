"""
Training service for automatic YOLO model fine-tuning on the archery dataset.

Handles:
- Dataset discovery, class verification, and sample counts
- Asynchronous training orchestration with live callback updates
- Real-time epoch progress, loss tracking, and validation metrics
- Results history parsing from results.csv
- Windows filesystem lock resilience
- Seamless hot-reloading into the active YOLOArrowDetectionService
"""

import os
import csv
import time
import glob
import yaml
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog

from src.schemas import (
    DatasetInfo,
    TrainingLossMetrics,
    TrainingEvaluationMetrics,
    TrainingStatusResponse,
    TrainingHistoryItem,
    TrainingHistoryResponse,
)

logger = structlog.get_logger()


class TrainingService:
    """Manages YOLO11 model training lifecycle and state."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TrainingService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        """Initialize service state and resolve directories."""
        self.workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.data_dir = os.path.join(self.workspace_root, "Data")
        self.runs_dir = os.path.join(self.workspace_root, "runs", "detect")
        self.run_name = "archery_yolo11"
        self.target_run_dir = os.path.join(self.runs_dir, self.run_name)
        self.weights_dir = os.path.join(self.target_run_dir, "weights")
        self.best_weights_path = os.path.join(self.weights_dir, "best.pt")
        self.last_weights_path = os.path.join(self.weights_dir, "last.pt")
        self.results_csv_path = os.path.join(self.target_run_dir, "results.csv")

        # Runtime training state
        self.is_running = False
        self.status = "idle"  # idle, running, completed, failed, stopped
        self.current_epoch = 0
        self.total_epochs = 0
        self.progress = 0.0
        self.start_time: Optional[float] = None
        self.start_time_iso: Optional[str] = None
        self.last_trained_at_iso: Optional[str] = None
        self.current_loss = TrainingLossMetrics()
        self.current_metrics = TrainingEvaluationMetrics()
        self.logs: List[str] = []
        self.max_logs = 100
        self.error_message: Optional[str] = None
        self._stop_requested = False
        self._training_thread: Optional[threading.Thread] = None

        # Check existing run on startup
        self._check_existing_run()

    def _add_log(self, message: str):
        """Append a timestamped log entry."""
        ts = datetime.utcnow().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.logs.append(entry)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        logger.info("training_log", message=message)

    def _check_existing_run(self):
        """Inspect filesystem for prior training checkpoints and results."""
        if os.path.exists(self.best_weights_path):
            mtime = os.path.getmtime(self.best_weights_path)
            self.last_trained_at_iso = datetime.fromtimestamp(mtime).isoformat()
            self.status = "completed"

        if os.path.exists(self.results_csv_path):
            try:
                history = self.get_history()
                if history and history.items:
                    last_item = history.items[-1]
                    self.current_epoch = last_item.epoch
                    self.total_epochs = history.total_epochs
                    self.progress = 100.0
                    self.current_loss = TrainingLossMetrics(
                        box_loss=last_item.train_box_loss,
                        cls_loss=last_item.train_cls_loss,
                        dfl_loss=last_item.train_dfl_loss,
                    )
                    self.current_metrics = TrainingEvaluationMetrics(
                        precision=last_item.precision,
                        recall=last_item.recall,
                        map50=last_item.map50,
                        map50_95=last_item.map50_95,
                    )
                    self._add_log(
                        f"Found prior model run with {history.total_epochs} epochs. Best mAP50: {history.best_map50 or 'N/A'}"
                    )
            except Exception as e:
                logger.warning("failed_to_parse_existing_results", error=str(e))

    def get_dataset_info(self) -> DatasetInfo:
        """Scan dataset directory and return sample counts and classes."""
        yaml_path = os.path.join(self.data_dir, "data.yaml")
        classes = ["2_ring", "4_ring", "6_ring", "7_ring", "arrow", "bullseye"]

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data_cfg = yaml.safe_load(f)
                    if isinstance(data_cfg, dict) and "names" in data_cfg:
                        names = data_cfg["names"]
                        if isinstance(names, list):
                            classes = names
                        elif isinstance(names, dict):
                            classes = [names[k] for k in sorted(names.keys())]
            except Exception as e:
                logger.warning("error_reading_data_yaml", error=str(e))

        def count_images(split_name: str) -> int:
            split_dir = os.path.join(self.data_dir, split_name, "images")
            if not os.path.exists(split_dir):
                return 0
            extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
            count = 0
            for ext in extensions:
                count += len(glob.glob(os.path.join(split_dir, ext)))
            return count

        train_count = count_images("train")
        val_count = count_images("valid")
        test_count = count_images("test")

        return DatasetInfo(
            name="Archery Scoring Dataset",
            path="Data",
            data_yaml="Data/data.yaml",
            train_images=train_count,
            val_images=val_count,
            test_images=test_count,
            total_images=train_count + val_count + test_count,
            classes=classes,
            status="ready" if train_count > 0 else "empty",
        )

    def get_status(self) -> TrainingStatusResponse:
        """Get the real-time training status and metrics."""
        elapsed = 0
        eta = None
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            if self.current_epoch > 0 and self.total_epochs > 0:
                sec_per_epoch = elapsed / self.current_epoch
                remaining_epochs = max(0, self.total_epochs - self.current_epoch)
                eta = int(sec_per_epoch * remaining_epochs)

        dataset = self.get_dataset_info()
        best_weights_exist = os.path.exists(self.best_weights_path)
        last_ckpt_exist = os.path.exists(self.last_weights_path)

        return TrainingStatusResponse(
            status=self.status,
            progress=round(self.progress, 1),
            current_epoch=self.current_epoch,
            total_epochs=self.total_epochs,
            start_time=self.start_time_iso,
            elapsed_seconds=elapsed,
            eta_seconds=eta,
            loss=self.current_loss,
            metrics=self.current_metrics,
            dataset=dataset,
            best_weights="runs/detect/archery_yolo11/weights/best.pt" if best_weights_exist else None,
            last_checkpoint="runs/detect/archery_yolo11/weights/last.pt" if last_ckpt_exist else None,
            weights_exist=best_weights_exist,
            last_trained_at=self.last_trained_at_iso,
            logs=list(self.logs),
            error=self.error_message,
        )

    def get_history(self) -> TrainingHistoryResponse:
        """Parse results.csv into structured history items."""
        if not os.path.exists(self.results_csv_path):
            return TrainingHistoryResponse(total_epochs=0, items=[])

        items: List[TrainingHistoryItem] = []
        best_map50 = None
        best_epoch = None

        try:
            with open(self.results_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}
                    try:
                        epoch_num = int(cleaned_row.get("epoch", 0))
                        time_sec = float(cleaned_row.get("time", 0.0)) if "time" in cleaned_row else None
                        
                        box_loss = float(cleaned_row.get("train/box_loss", 0.0)) if "train/box_loss" in cleaned_row else None
                        cls_loss = float(cleaned_row.get("train/cls_loss", 0.0)) if "train/cls_loss" in cleaned_row else None
                        dfl_loss = float(cleaned_row.get("train/dfl_loss", 0.0)) if "train/dfl_loss" in cleaned_row else None

                        prec = float(cleaned_row.get("metrics/precision(B)", 0.0)) if "metrics/precision(B)" in cleaned_row else None
                        rec = float(cleaned_row.get("metrics/recall(B)", 0.0)) if "metrics/recall(B)" in cleaned_row else None
                        m50 = float(cleaned_row.get("metrics/mAP50(B)", 0.0)) if "metrics/mAP50(B)" in cleaned_row else None
                        m50_95 = float(cleaned_row.get("metrics/mAP50-95(B)", 0.0)) if "metrics/mAP50-95(B)" in cleaned_row else None

                        v_box = float(cleaned_row.get("val/box_loss", 0.0)) if "val/box_loss" in cleaned_row else None
                        v_cls = float(cleaned_row.get("val/cls_loss", 0.0)) if "val/cls_loss" in cleaned_row else None
                        v_dfl = float(cleaned_row.get("val/dfl_loss", 0.0)) if "val/dfl_loss" in cleaned_row else None

                        if m50 is not None:
                            if best_map50 is None or m50 > best_map50:
                                best_map50 = m50
                                best_epoch = epoch_num

                        items.append(
                            TrainingHistoryItem(
                                epoch=epoch_num,
                                time_seconds=time_sec,
                                train_box_loss=box_loss,
                                train_cls_loss=cls_loss,
                                train_dfl_loss=dfl_loss,
                                precision=prec,
                                recall=rec,
                                map50=m50,
                                map50_95=m50_95,
                                val_box_loss=v_box,
                                val_cls_loss=v_cls,
                                val_dfl_loss=v_dfl,
                            )
                        )
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.error("error_parsing_history", error=str(e))

        file_size = os.path.getsize(self.best_weights_path) if os.path.exists(self.best_weights_path) else None
        mtime_str = None
        if os.path.exists(self.best_weights_path):
            mtime_str = datetime.fromtimestamp(os.path.getmtime(self.best_weights_path)).isoformat()

        return TrainingHistoryResponse(
            total_epochs=len(items),
            items=items,
            best_map50=best_map50,
            best_epoch=best_epoch,
            weights_file="runs/detect/archery_yolo11/weights/best.pt" if os.path.exists(self.best_weights_path) else None,
            weights_size_bytes=file_size,
            weights_last_modified=mtime_str,
        )

    def start_training(
        self,
        epochs: int = 3,
        batch_size: int = 4,
        imgsz: int = 896,
        device: str = "cpu",
        resume: bool = False,
    ):
        """
        Initiate asynchronous YOLO model training with available dataset.
        """
        with self._lock:
            if self.is_running:
                raise RuntimeError("Training is already currently in progress.")

            # Validate dataset
            dataset_info = self.get_dataset_info()
            if dataset_info.train_images == 0:
                raise ValueError("No training images found in Data/train/images.")

            self.is_running = True
            self.status = "running"
            self.total_epochs = epochs
            self.current_epoch = 0
            self.progress = 0.0
            self.start_time = time.time()
            self.start_time_iso = datetime.utcnow().isoformat()
            self.error_message = None
            self._stop_requested = False
            self.logs = []

        self._add_log(f"Training initiated: {epochs} epochs, batch {batch_size}, imgsz {imgsz}, device {device}")
        self._add_log(f"Dataset verified: {dataset_info.train_images} train, {dataset_info.val_images} val images, {len(dataset_info.classes)} classes.")

        self._training_thread = threading.Thread(
            target=self._run_training_worker,
            args=(epochs, batch_size, imgsz, device, resume),
            daemon=True,
        )
        self._training_thread.start()

    def _run_training_worker(
        self,
        epochs: int,
        batch_size: int,
        imgsz: int,
        device: str,
        resume: bool,
    ):
        """Worker thread executing Ultralytics YOLO training."""
        try:
            from ultralytics import YOLO
            from ultralytics.engine.trainer import BaseTrainer

            # Windows file lock resilience patch
            orig_save_model = BaseTrainer.save_model

            def resilient_save_model(trainer_self):
                max_attempts = 6
                for attempt in range(max_attempts):
                    try:
                        return orig_save_model(trainer_self)
                    except OSError as err:
                        wait_time = 0.5 * (attempt + 1)
                        time.sleep(wait_time)
                return False

            BaseTrainer.save_model = resilient_save_model

            # Prepare robust dataset configuration for current environment
            yaml_path = os.path.join(self.data_dir, "data.yaml")
            resolved_yaml_path = os.path.join(self.data_dir, "runtime_data.yaml")
            
            cfg_dict = {
                "path": self.data_dir,
                "train": "train/images",
                "val": "valid/images",
                "test": "test/images",
                "nc": 6,
                "names": ['2_ring', '4_ring', '6_ring', '7_ring', 'arrow', 'bullseye']
            }
            if os.path.exists(yaml_path):
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f)
                        if isinstance(loaded, dict):
                            cfg_dict.update(loaded)
                except Exception:
                    pass
                    
            cfg_dict["path"] = self.data_dir
            with open(resolved_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg_dict, f)

            # Check starting model weights
            base_model_path = os.path.join(self.workspace_root, "yolo11n.pt")
            if not os.path.exists(base_model_path):
                base_model_path = "yolo11n.pt"

            checkpoint_last = self.last_weights_path
            should_resume = resume and os.path.exists(checkpoint_last)

            if should_resume:
                self._add_log(f"Resuming training from checkpoint: {checkpoint_last}")
                model = YOLO(checkpoint_last)
            else:
                self._add_log(f"Loading base architecture: {base_model_path}")
                model = YOLO(base_model_path)

            # Register Ultralytics callbacks
            def on_train_epoch_start(trainer):
                if self._stop_requested:
                    trainer.stop = True
                    self._add_log("Training cancellation requested by user.")
                    return
                epoch = trainer.epoch + 1
                self.current_epoch = epoch
                self.progress = round(((epoch - 1) / epochs) * 100, 1)
                self._add_log(f"Epoch {epoch}/{epochs} started...")

            def on_fit_epoch_end(trainer):
                epoch = trainer.epoch + 1
                self.current_epoch = epoch
                self.progress = round((epoch / epochs) * 100, 1)

                # Extract loss metrics
                loss_items = getattr(trainer, "loss_items", None)
                if loss_items is not None and len(loss_items) >= 3:
                    try:
                        b_loss = float(loss_items[0])
                        c_loss = float(loss_items[1])
                        d_loss = float(loss_items[2])
                        tot = b_loss + c_loss + d_loss
                        self.current_loss = TrainingLossMetrics(
                            box_loss=round(b_loss, 4),
                            cls_loss=round(c_loss, 4),
                            dfl_loss=round(d_loss, 4),
                            total_loss=round(tot, 4),
                        )
                    except Exception:
                        pass

                # Extract validation metrics
                metrics = getattr(trainer, "metrics", {}) or {}
                prec = metrics.get("metrics/precision(B)")
                rec = metrics.get("metrics/recall(B)")
                m50 = metrics.get("metrics/mAP50(B)")
                m50_95 = metrics.get("metrics/mAP50-95(B)")

                self.current_metrics = TrainingEvaluationMetrics(
                    precision=round(float(prec), 4) if prec is not None else self.current_metrics.precision,
                    recall=round(float(rec), 4) if rec is not None else self.current_metrics.recall,
                    map50=round(float(m50), 4) if m50 is not None else self.current_metrics.map50,
                    map50_95=round(float(m50_95), 4) if m50_95 is not None else self.current_metrics.map50_95,
                )

                log_summary = f"Epoch {epoch}/{epochs} finished"
                if m50 is not None:
                    log_summary += f" | mAP50: {float(m50)*100:.1f}%"
                if self.current_loss.total_loss is not None:
                    log_summary += f" | Loss: {self.current_loss.total_loss:.3f}"
                self._add_log(log_summary)

            def on_train_batch_end(trainer):
                if self._stop_requested:
                    trainer.stop = True

            model.add_callback("on_train_epoch_start", on_train_epoch_start)
            model.add_callback("on_train_batch_end", on_train_batch_end)
            model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

            # Run training
            self._add_log("Commencing model fit on available archery dataset...")
            if should_resume:
                results = model.train(resume=True)
            else:
                results = model.train(
                    data=resolved_yaml_path,
                    epochs=epochs,
                    imgsz=imgsz,
                    batch=batch_size,
                    device=device,
                    workers=2,
                    project=self.runs_dir,
                    name=self.run_name,
                    cache=True,
                    exist_ok=True,
                )

            if self._stop_requested:
                self.status = "stopped"
                self._add_log("Training stopped by user request.")
            else:
                self.status = "completed"
                self.progress = 100.0
                self.last_trained_at_iso = datetime.utcnow().isoformat()
                self._add_log("Training completed successfully! Model weights saved.")
                self.reload_active_model()

        except Exception as e:
            logger.exception("training_worker_error", error=str(e))
            self.status = "failed"
            self.error_message = str(e)
            self._add_log(f"Training error: {str(e)}")
        finally:
            self.is_running = False

    def stop_training(self):
        """Signal the training worker to abort after current step."""
        with self._lock:
            if not self.is_running:
                return
            self._stop_requested = True
            self._add_log("Aborting training pipeline...")

    def reload_active_model(self) -> Dict[str, Any]:
        """Hot-reload newly trained best.pt weights into image inference pipeline."""
        try:
            from src.services.image_service import _yolo_detector
            if _yolo_detector is not None:
                _yolo_detector._load_model()
                self._add_log("Live YOLO inference engine reloaded with latest weights.")
                return {"status": "ok", "message": "Model reloaded into inference service successfully"}
            return {"status": "warning", "message": "Inference service not initialized"}
        except Exception as e:
            logger.exception("reload_active_model_error", error=str(e))
            return {"status": "error", "message": f"Failed to reload model: {str(e)}"}


# Global singleton instance
training_service = TrainingService()
