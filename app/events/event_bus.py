"""
Event Bus System for Nexus Miracle.
Provides async publish/subscribe pattern for real-time updates.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for the system."""
    
    # Appointment events
    APPOINTMENT_CREATED = "appointment.created"
    APPOINTMENT_UPDATED = "appointment.updated"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    APPOINTMENT_CONFIRMED = "appointment.confirmed"
    
    # Call events
    CALL_STARTED = "call.started"
    CALL_ENDED = "call.ended"
    CALL_ERROR = "call.error"
    
    # Settings events
    SETTINGS_UPDATED = "settings.updated"
    VOICE_SETTINGS_UPDATED = "voice_settings.updated"
    FILLERS_UPDATED = "fillers.updated"
    PROMPT_UPDATED = "prompt.updated"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system.health_check"


@dataclass
class Event:
    """Event data structure."""
    
    type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    correlation_id: str | None = None
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for serialization."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async Event Bus for publish/subscribe pattern.
    
    Usage:
        bus = EventBus()
        
        # Subscribe to events
        @bus.on(EventType.APPOINTMENT_CREATED)
        async def handle_appointment(event: Event):
            print(f"New appointment: {event.data}")
        
        # Publish events
        await bus.publish(EventType.APPOINTMENT_CREATED, {
            "patient": "عمر",
            "doctor": "د. فهد",
            "time": "10:00"
        })
    """
    
    _instance: "EventBus | None" = None
    
    def __new__(cls) -> "EventBus":
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._websocket_clients: list[Any] = []
        self._event_history: list[Event] = []
        self._max_history = 100
        self._initialized = True
        
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe from an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Handler unsubscribed from {event_type.value}")
    
    def on(self, event_type: EventType) -> Callable[[EventHandler], EventHandler]:
        """Decorator to subscribe a handler to an event type."""
        def decorator(handler: EventHandler) -> EventHandler:
            self.subscribe(event_type, handler)
            return handler
        return decorator
    
    async def publish(
        self,
        event_type: EventType,
        data: dict[str, Any],
        source: str = "system",
        correlation_id: str | None = None,
    ) -> None:
        """Publish an event to all subscribers."""
        event = Event(
            type=event_type,
            data=data,
            source=source,
            correlation_id=correlation_id,
        )
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        logger.info(f"Publishing event: {event_type.value} from {source}")
        
        # Notify all subscribers
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            await asyncio.gather(
                *[self._safe_call(handler, event) for handler in handlers],
                return_exceptions=True,
            )
        
        # Broadcast to WebSocket clients
        await self._broadcast_websocket(event)
    
    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Safely call a handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in event handler: {e}", exc_info=True)
    
    async def _broadcast_websocket(self, event: Event) -> None:
        """Broadcast event to all connected WebSocket clients."""
        if not self._websocket_clients:
            return
        
        message = event.to_dict()
        disconnected = []
        
        for client in self._websocket_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket client: {e}")
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            self._websocket_clients.remove(client)
    
    def register_websocket(self, client: Any) -> None:
        """Register a WebSocket client for broadcasts."""
        self._websocket_clients.append(client)
        logger.info(f"WebSocket client registered. Total: {len(self._websocket_clients)}")
    
    def unregister_websocket(self, client: Any) -> None:
        """Unregister a WebSocket client."""
        if client in self._websocket_clients:
            self._websocket_clients.remove(client)
            logger.info(f"WebSocket client unregistered. Total: {len(self._websocket_clients)}")
    
    def get_history(self, event_type: EventType | None = None, limit: int = 10) -> list[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]
    
    def clear(self) -> None:
        """Clear all subscribers and history. Useful for testing."""
        self._subscribers.clear()
        self._event_history.clear()
        self._websocket_clients.clear()


# Global event bus instance
event_bus = EventBus()


# Convenience functions
async def publish_event(
    event_type: EventType,
    data: dict[str, Any],
    source: str = "system",
) -> None:
    """Publish an event using the global event bus."""
    await event_bus.publish(event_type, data, source)


def subscribe_event(event_type: EventType, handler: EventHandler) -> None:
    """Subscribe to an event using the global event bus."""
    event_bus.subscribe(event_type, handler)
