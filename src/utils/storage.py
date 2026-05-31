"""
File storage utilities for image and report management.

Pattern #9: Storage Management

Handles file organization, quota enforcement, and archival.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple
import uuid
import structlog

logger = structlog.get_logger()


class StorageManager:
    """
    Manages file storage for images, reports, and archives.

    Pattern #9: Storage Management

    Structure:
    - /storage/raw/{session_id}/ - Original captured images (JPEG quality 70)
    - /storage/annotated/{session_id}/ - Processed images with annotations
    - /storage/reports/{session_id}/ - Generated reports (PDF, CSV, JSON)
    - /storage/archives/ - Compressed archives of old images (tar.gz)
    """

    def __init__(self, base_path: str = "/storage", quota_bytes: int = 10 * 1024 * 1024 * 1024):
        """
        Initialize storage manager.

        Args:
            base_path: Root storage directory
            quota_bytes: Storage quota in bytes (default 10GB)
        """
        self.base_path = Path(base_path)
        self.quota_bytes = quota_bytes

        # Create directories
        self.raw_dir = self.base_path / "raw"
        self.annotated_dir = self.base_path / "annotated"
        self.reports_dir = self.base_path / "reports"
        self.archives_dir = self.base_path / "archives"

        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all storage directories exist."""
        for dir_path in [self.raw_dir, self.annotated_dir, self.reports_dir, self.archives_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug("storage_directory_created", path=str(dir_path))

    def get_session_raw_path(self, session_id: int) -> Path:
        """Get path for session's raw images directory."""
        path = self.raw_dir / str(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_session_annotated_path(self, session_id: int) -> Path:
        """Get path for session's annotated images directory."""
        path = self.annotated_dir / str(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_session_reports_path(self, session_id: int) -> Path:
        """Get path for session's reports directory."""
        path = self.reports_dir / str(session_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_image(self, image_bytes: bytes, session_id: int, image_type: str = "raw") -> Tuple[bool, str, str]:
        """
        Save image to storage.

        Args:
            image_bytes: Image data
            session_id: Session ID
            image_type: Type of image (raw|annotated)

        Returns:
            (success, image_id, file_path) tuple
        """
        # Check quota
        current_usage = self.get_storage_usage_bytes()
        if current_usage + len(image_bytes) > self.quota_bytes:
            logger.warning("storage_quota_exceeded", current_usage=current_usage, requested=len(image_bytes))
            return False, "", "Storage quota exceeded"

        # Generate unique image ID
        image_id = str(uuid.uuid4())

        # Get appropriate directory
        if image_type == "raw":
            directory = self.get_session_raw_path(session_id)
        elif image_type == "annotated":
            directory = self.get_session_annotated_path(session_id)
        else:
            return False, "", f"Invalid image type: {image_type}"

        # Save file
        file_path = directory / f"{image_id}.jpg"

        try:
            with open(file_path, "wb") as f:
                f.write(image_bytes)

            logger.info("image_saved", image_id=image_id, session_id=session_id, type=image_type, size_bytes=len(image_bytes))
            return True, image_id, str(file_path)

        except Exception as e:
            logger.exception("image_save_error", error=str(e))
            return False, "", str(e)

    def save_report(self, report_bytes: bytes, session_id: int, format: str) -> Tuple[bool, str]:
        """
        Save report to storage.

        Args:
            report_bytes: Report data
            session_id: Session ID
            format: Report format (pdf|csv|json)

        Returns:
            (success, file_path) tuple
        """
        # Check quota
        current_usage = self.get_storage_usage_bytes()
        if current_usage + len(report_bytes) > self.quota_bytes:
            logger.warning("storage_quota_exceeded_report", current_usage=current_usage)
            return False, "Storage quota exceeded"

        directory = self.get_session_reports_path(session_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = directory / f"report_{timestamp}.{format}"

        try:
            with open(file_path, "wb") as f:
                f.write(report_bytes)

            logger.info("report_saved", session_id=session_id, format=format, size_bytes=len(report_bytes))
            return True, str(file_path)

        except Exception as e:
            logger.exception("report_save_error", error=str(e))
            return False, str(e)

    def archive_old_images(self, days: int = 90) -> Tuple[bool, int]:
        """
        Archive images older than specified days.

        Pattern #9: Storage Management (90-day rotation)

        Args:
            days: Age threshold in days

        Returns:
            (success, archived_count) tuple
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        archived_count = 0

        try:
            # Process raw images
            for session_dir in self.raw_dir.iterdir():
                if session_dir.is_dir():
                    # Check directory modification time
                    mod_time = datetime.fromtimestamp(session_dir.stat().st_mtime)
                    
                    if mod_time < cutoff_date:
                        # Create archive
                        archive_name = f"archive_{session_dir.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tar.gz"
                        archive_path = self.archives_dir / archive_name

                        shutil.make_archive(
                            str(archive_path.parent / archive_path.stem),
                            "gztar",
                            session_dir,
                        )

                        # Delete original
                        shutil.rmtree(session_dir)
                        archived_count += 1

                        logger.info("images_archived", session_id=session_dir.name, archive=archive_name)

            return True, archived_count

        except Exception as e:
            logger.exception("archive_error", error=str(e))
            return False, archived_count

    def get_storage_usage_bytes(self) -> int:
        """
        Calculate total storage usage.

        Returns:
            Total bytes used
        """
        total_bytes = 0

        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_bytes += os.path.getsize(file_path)
                except OSError:
                    pass

        return total_bytes

    def get_storage_usage_gb(self) -> float:
        """
        Get storage usage in GB.

        Returns:
            Storage usage in GB
        """
        return self.get_storage_usage_bytes() / (1024 * 1024 * 1024)

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with usage stats
        """
        used_bytes = self.get_storage_usage_bytes()
        used_gb = used_bytes / (1024 * 1024 * 1024)
        quota_gb = self.quota_bytes / (1024 * 1024 * 1024)
        usage_percent = (used_bytes / self.quota_bytes) * 100 if self.quota_bytes > 0 else 0

        return {
            "used_bytes": used_bytes,
            "used_gb": round(used_gb, 2),
            "quota_bytes": self.quota_bytes,
            "quota_gb": round(quota_gb, 2),
            "usage_percent": round(usage_percent, 1),
            "available_gb": round(quota_gb - used_gb, 2),
        }

    def cleanup_session_storage(self, session_id: int) -> Tuple[bool, int]:
        """
        Delete all files for a session.

        Args:
            session_id: Session ID

        Returns:
            (success, deleted_count) tuple
        """
        deleted_count = 0

        try:
            for directory in [self.raw_dir, self.annotated_dir, self.reports_dir]:
                session_path = directory / str(session_id)
                
                if session_path.exists():
                    for file_path in session_path.rglob("*"):
                        if file_path.is_file():
                            file_path.unlink()
                            deleted_count += 1
                    
                    session_path.rmdir()

            logger.info("session_storage_cleaned", session_id=session_id, deleted_count=deleted_count)
            return True, deleted_count

        except Exception as e:
            logger.exception("cleanup_error", session_id=session_id, error=str(e))
            return False, deleted_count


# Global storage manager instance
storage_manager = None


def get_storage_manager(base_path: str = "/storage", quota_bytes: int = 10 * 1024 * 1024 * 1024) -> StorageManager:
    """Get or create global storage manager instance."""
    global storage_manager
    
    if storage_manager is None:
        storage_manager = StorageManager(base_path, quota_bytes)
    
    return storage_manager
