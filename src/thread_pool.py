"""
Global thread pool executor for image processing.

This module provides a global ThreadPoolExecutor instance that is initialized
during application startup and used for CPU-bound tasks like image processing.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Global thread pool executor for image processing
_executor: Optional[ThreadPoolExecutor] = None


def set_executor(executor: ThreadPoolExecutor) -> None:
    """Set the global thread pool executor."""
    global _executor
    _executor = executor


def get_executor() -> Optional[ThreadPoolExecutor]:
    """Get the global thread pool executor."""
    return _executor


def shutdown_executor() -> None:
    """Shutdown the global thread pool executor."""
    global _executor
    if _executor:
        _executor.shutdown(wait=True)
        _executor = None
