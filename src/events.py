"""
Event bus module for in-process pub/sub event publishing.

Handles:
- Event publishing and subscription
- Event routing to subscribers
- Fire-and-forget event delivery (MVP soft real-time)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List

import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    """Enumeration of event types emitted by the system."""

    # Authentication events
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_PASSWORD_RESET = "user.password_reset"

    # Tournament/Session events
    TOURNAMENT_CREATED = "tournament.created"
    SESSION_CREATED = "session.created"
    SESSION_STATE_CHANGED = "session.state_changed"
    SESSION_COMPLETED = "session.completed"

    # Scoring events
    SCORE_RECORDED = "score.recorded"
    SCORE_CALCULATED = "score.calculated"
    SCORE_VALIDATED = "score.validated"

    # Camera events
    CAMERA_CONNECTED = "camera.connected"
    CAMERA_DISCONNECTED = "camera.disconnected"
    CAMERA_RECONNECTION_STARTED = "camera.reconnection_started"
    CAMERA_RECONNECTION_FAILED = "camera.reconnection_failed"

    # Leaderboard events
    LEADERBOARD_UPDATED = "leaderboard.updated"

    # Storage events
    STORAGE_ARCHIVED = "storage.archived"

    # System events
    ERROR_OCCURRED = "error.occurred"
    HEALTH_CHECK_FAILED = "health_check.failed"


@dataclass
class Event:
    """Represents an event in the system."""

    event_type: EventType
    data: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            from datetime import datetime

            self.timestamp = datetime.utcnow().isoformat()


class EventBus:
    """
    In-process event bus for publish/subscribe pattern.

    Used for:
    - Score updates → WebSocket broadcasts
    - Cache invalidation on score/leaderboard updates
    - Camera status changes
    - Audit logging
    """

    def __init__(self):
        """Initialize event bus."""
        self.subscribers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable):
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callable to invoke when event is published
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)
        logger.info("event_subscribed", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                h for h in self.subscribers[event_type] if h != handler
            ]

    def publish(self, event: Event):
        """
        Publish an event to all subscribers (fire-and-forget).

        Args:
            event: Event to publish

        Note:
            Errors in handlers are logged but don't propagate.
            Target latency: < 500ms (soft real-time for MVP)
        """
        handlers = self.subscribers.get(event.event_type, [])

        logger.info(
            "event_published",
            event_type=event.event_type,
            subscriber_count=len(handlers),
            data=event.data,
        )

        for handler in handlers:
            try:
                import inspect
                import asyncio
                if inspect.iscoroutinefunction(handler):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event))
                    except RuntimeError:
                        asyncio.run(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.exception("event_handler_error", handler=handler.__name__, error=str(e))


# Global event bus instance
event_bus = EventBus()


def publish_event(event_type: EventType, data: Dict[str, Any]):
    """
    Convenience function to publish an event.

    Args:
        event_type: Type of event
        data: Event data
    """
    event = Event(event_type=event_type, data=data)
    event_bus.publish(event)


def subscribe_to_event(event_type: EventType, handler: Callable):
    """
    Convenience function to subscribe to an event.

    Args:
        event_type: Type of event
        handler: Callable to invoke
    """
    event_bus.subscribe(event_type, handler)
