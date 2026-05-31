"""
Health check service for system monitoring and diagnostics.

Provides component status for:
- Database connectivity
- Redis cache connectivity
- Storage availability
- ThreadPool executor status

Story coverage: US-6.2 (database resilience, health checks)
"""

import os
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import structlog

from src.database import SessionLocal, verify_database_connectivity
from src.cache import cache_manager
from src.config import settings
from src.main import thread_pool_executor

logger = structlog.get_logger()


class HealthService:
    """System health check service."""

    @staticmethod
    async def get_system_health() -> Dict[str, Any]:
        """
        Get overall system health status.

        Returns:
            Dictionary with status and component details
        """
        components = {}

        # Check database
        components["database"] = HealthService.check_database_health()

        # Check cache
        components["cache"] = HealthService.check_cache_health()

        # Check storage
        components["storage"] = HealthService.check_storage_health()

        # Check threadpool
        components["threadpool"] = HealthService.check_threadpool_health()

        # Determine overall status
        all_ok = all(c.get("status") == "ok" for c in components.values())
        any_degraded = any(c.get("status") == "degraded" for c in components.values())

        if all_ok:
            status = "ok"
        elif any_degraded:
            status = "degraded"
        else:
            status = "down"

        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
        }

    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        """
        Check database connectivity.

        Returns:
            Status dictionary
        """
        try:
            is_connected = verify_database_connectivity()

            if is_connected:
                return {
                    "status": "ok",
                    "message": "Database connected",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "down",
                    "message": "Database connection failed",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.warning("database_health_check_error", error=str(e))
            return {
                "status": "down",
                "message": f"Database health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def check_cache_health() -> Dict[str, Any]:
        """
        Check Redis cache connectivity.

        Returns:
            Status dictionary
        """
        try:
            is_connected = cache_manager.ping()

            if is_connected:
                return {
                    "status": "ok",
                    "message": "Cache connected",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "degraded",
                    "message": "Cache connection failed",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.warning("cache_health_check_error", error=str(e))
            return {
                "status": "degraded",
                "message": f"Cache health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def check_storage_health() -> Dict[str, Any]:
        """
        Check storage availability and quota.

        Returns:
            Status dictionary with usage info
        """
        try:
            storage_path = settings.storage_path

            if not os.path.exists(storage_path):
                os.makedirs(storage_path, exist_ok=True)

            # Calculate usage
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(storage_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)

            used_gb = total_size / (1024 ** 3)
            quota_gb = settings.storage_quota_gb

            if used_gb > quota_gb:
                status = "down"
                message = "Storage quota exceeded"
            elif used_gb > (quota_gb * 0.9):  # 90% threshold
                status = "degraded"
                message = "Storage usage high (>90%)"
            else:
                status = "ok"
                message = "Storage ok"

            return {
                "status": status,
                "message": message,
                "used_gb": round(used_gb, 2),
                "quota_gb": quota_gb,
                "usage_percent": round((used_gb / quota_gb) * 100, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.warning("storage_health_check_error", error=str(e))
            return {
                "status": "degraded",
                "message": f"Storage health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    @staticmethod
    def check_threadpool_health() -> Dict[str, Any]:
        """
        Check ThreadPool executor status.

        Returns:
            Status dictionary with pool info
        """
        try:
            if thread_pool_executor is None:
                return {
                    "status": "down",
                    "message": "ThreadPool not initialized",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            active_count = thread_pool_executor._work_queue.qsize()  # Approximate
            max_workers = thread_pool_executor._max_workers

            # Check if pool is responsive
            health_future = thread_pool_executor.submit(lambda: True)
            try:
                health_future.result(timeout=1)
                is_responsive = True
            except Exception:
                is_responsive = False

            status = "ok" if is_responsive else "degraded"
            utilization = round((active_count / max_workers) * 100, 1) if max_workers > 0 else 0

            return {
                "status": status,
                "message": "ThreadPool ok" if status == "ok" else "ThreadPool degraded",
                "active_workers": active_count,
                "max_workers": max_workers,
                "utilization_percent": utilization,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.warning("threadpool_health_check_error", error=str(e))
            return {
                "status": "degraded",
                "message": f"ThreadPool health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
