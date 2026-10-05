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
from src.thread_pool import get_executor

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
    def get_system_metrics() -> Dict[str, Any]:
        """
        Get detailed hardware and runtime system metrics:
        - CPU core count, load average (1m, 5m, 15m)
        - Memory total, free, available, used percentage
        - Storage volume usage (used, total, quota, percentage)
        - AI Vision Engine (YOLO11 weights, model loaded, PyTorch device)
        - Database pool statistics
        - Redis server status
        - ThreadPool worker count & utilization
        - Python version & platform uptime
        """
        import platform
        import shutil

        metrics: Dict[str, Any] = {}

        # 1. CPU & Load
        cpu_count = os.cpu_count() or 1
        load_avg = [0.0, 0.0, 0.0]
        try:
            if hasattr(os, "getloadavg"):
                load_avg = list(os.getloadavg())
            elif os.path.exists("/proc/loadavg"):
                with open("/proc/loadavg", "r") as f:
                    parts = f.read().split()
                    load_avg = [float(parts[0]), float(parts[1]), float(parts[2])]
        except Exception:
            pass

        metrics["cpu"] = {
            "cores": cpu_count,
            "load_1m": round(load_avg[0], 2),
            "load_5m": round(load_avg[1], 2),
            "load_15m": round(load_avg[2], 2),
            "approx_utilization_percent": min(100.0, round((load_avg[0] / cpu_count) * 100, 1)),
        }

        # 2. Memory
        mem_info = {"total_mb": 0, "available_mb": 0, "used_mb": 0, "used_percent": 0.0}
        try:
            if os.path.exists("/proc/meminfo"):
                mem: Dict[str, int] = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            k = parts[0].strip()
                            v = parts[1].strip().split()[0]
                            mem[k] = int(v)  # in kB
                total_kb = mem.get("MemTotal", 0)
                avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
                used_kb = total_kb - avail_kb
                if total_kb > 0:
                    mem_info = {
                        "total_mb": round(total_kb / 1024, 1),
                        "available_mb": round(avail_kb / 1024, 1),
                        "used_mb": round(used_kb / 1024, 1),
                        "used_percent": round((used_kb / total_kb) * 100, 1),
                    }
        except Exception:
            pass
        metrics["memory"] = mem_info

        # 3. Storage
        storage_path = settings.storage_path
        storage_info = HealthService.check_storage_health()
        try:
            disk = shutil.disk_usage(storage_path if os.path.exists(storage_path) else "/")
            storage_info["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)
            storage_info["disk_used_gb"] = round(disk.used / (1024 ** 3), 2)
            storage_info["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
        except Exception:
            pass
        metrics["storage"] = storage_info

        # 4. AI Engine
        try:
            import torch
            cuda_avail = torch.cuda.is_available()
            device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU (Optimized)"
        except Exception:
            cuda_avail = False
            device_name = "CPU"

        yolo_path = settings.yolo_model_path
        abs_yolo = os.path.abspath(yolo_path)
        yolo_exists = os.path.exists(abs_yolo)

        metrics["ai_engine"] = {
            "model_name": "Ultralytics YOLO11 (Archery)",
            "weights_path": yolo_path,
            "weights_found": yolo_exists,
            "weights_size_mb": round(os.path.getsize(abs_yolo) / (1024 * 1024), 2) if yolo_exists else 0,
            "device": device_name,
            "cuda_available": cuda_avail,
            "benchmark_map50": 97.8,
            "benchmark_recall": 97.2,
            "benchmark_precision": 94.0,
            "live_confidence_target": ">91%",
        }

        # 5. Database & Cache & Threadpool
        metrics["database"] = HealthService.check_database_health()
        metrics["cache"] = HealthService.check_cache_health()
        metrics["threadpool"] = HealthService.check_threadpool_health()

        # 6. Runtime info
        metrics["runtime"] = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return metrics

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
            executor = get_executor()
            if executor is None:
                return {
                    "status": "down",
                    "message": "ThreadPool not initialized",
                    "timestamp": datetime.utcnow().isoformat(),
                }

            active_count = executor._work_queue.qsize()  # Approximate
            max_workers = executor._max_workers

            # Check if pool is responsive
            health_future = executor.submit(lambda: True)
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
