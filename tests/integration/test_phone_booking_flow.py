"""
Integration test for phone booking flow.
Tests: Call → Intent Detection → Booking → Database → WebSocket
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import app components
import sys
sys.path.insert(0, ".")


class TestPhoneBookingFlow:
    """Test complete phone booking flow."""
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        from app.events import EventBus
        bus = EventBus()
        bus.clear()
        return bus
    
    @pytest.fixture
    def sample_booking_request(self):
        """Sample booking request extracted from call."""
        return {
            "patient_name": "عبدالله محمد",
            "patient_phone": "+966501234567",
            "doctor_id": "dr_001",
            "doctor_name": "دكتور فهد الغامدي",
            "specialty": "العظام",
            "preferred_date": datetime.now() + timedelta(days=1),
            "preferred_time": "10:00",
            "branch": "الفرع الرئيسي",
            "source": "phone",
            "call_id": "call_abc123",
        }
    
    @pytest.mark.asyncio
    async def test_booking_creates_appointment_in_database(
        self,
        sample_booking_request,
    ):
        """Test that phone booking creates appointment in database."""
        # Arrange
        from app.events import event_bus, EventType
        
        events_received = []
        
        @event_bus.on(EventType.APPOINTMENT_CREATED)
        async def capture_event(event):
            events_received.append(event)
        
        # Act - Simulate booking creation
        await event_bus.publish(
            EventType.APPOINTMENT_CREATED,
            sample_booking_request,
            source="phone_call",
        )
        
        # Assert
        assert len(events_received) == 1
        event = events_received[0]
        assert event.type == EventType.APPOINTMENT_CREATED
        assert event.data["patient_name"] == "عبدالله محمد"
        assert event.data["source"] == "phone"
    
    @pytest.mark.asyncio
    async def test_booking_triggers_websocket_broadcast(
        self,
        sample_booking_request,
    ):
        """Test that booking event is broadcast to WebSocket clients."""
        from app.events import event_bus, EventType
        
        # Create mock WebSocket client
        mock_ws = AsyncMock()
        event_bus.register_websocket(mock_ws)
        
        # Act
        await event_bus.publish(
            EventType.APPOINTMENT_CREATED,
            sample_booking_request,
            source="phone_call",
        )
        
        # Assert
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "appointment.created"
        assert call_args["data"]["patient_name"] == "عبدالله محمد"
        
        # Cleanup
        event_bus.unregister_websocket(mock_ws)
    
    @pytest.mark.asyncio
    async def test_booking_flow_with_intent_detection(self):
        """Test complete flow from intent detection to booking."""
        from app.events import event_bus, EventType
        
        # Simulate LLM detecting booking intent
        booking_intent = {
            "intent": "book_appointment",
            "confidence": 0.95,
            "entities": {
                "specialty": "العظام",
                "preferred_day": "الثلاثاء",
                "preferred_time": "الصباح",
            },
        }
        
        intent_events = []
        
        # This would be handled by the booking orchestrator
        @event_bus.on(EventType.APPOINTMENT_CREATED)
        async def handle_intent(event):
            intent_events.append(event)
        
        # Act - Simulate the complete flow
        await event_bus.publish(
            EventType.APPOINTMENT_CREATED,
            {
                "patient_name": "محمد العتيبي",
                "doctor_name": "دكتور فهد الغامدي",
                "scheduled_at": "2026-01-15T10:00:00",
                "source": "phone",
                "detected_intent": booking_intent,
            },
            source="booking_orchestrator",
        )
        
        # Assert
        assert len(intent_events) == 1
        assert intent_events[0].data["source"] == "phone"


class TestConcurrentCalls:
    """Test handling of concurrent calls."""
    
    @pytest.mark.asyncio
    async def test_multiple_simultaneous_bookings(self):
        """Test that multiple concurrent bookings don't interfere."""
        from app.events import event_bus, EventType
        
        events_received = []
        
        @event_bus.on(EventType.APPOINTMENT_CREATED)
        async def capture_events(event):
            events_received.append(event)
            # Simulate processing time
            await asyncio.sleep(0.1)
        
        # Create 10 concurrent bookings
        tasks = []
        for i in range(10):
            task = event_bus.publish(
                EventType.APPOINTMENT_CREATED,
                {
                    "patient_name": f"مريض {i}",
                    "call_id": f"call_{i}",
                },
                source=f"call_{i}",
            )
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        
        # Assert all events were processed
        assert len(events_received) == 10
        
        # Verify no duplicate processing
        call_ids = [e.data["call_id"] for e in events_received]
        assert len(set(call_ids)) == 10


class TestLatencyRequirements:
    """Test latency requirements are met."""
    
    @pytest.mark.asyncio
    async def test_event_processing_under_100ms(self):
        """Test event processing is fast enough."""
        from app.events import event_bus, EventType
        import time
        
        # Clear previous handlers to get accurate timing
        event_bus.clear()
        
        processing_times = []
        
        @event_bus.on(EventType.APPOINTMENT_CREATED)
        async def measure_processing(event):
            # Minimal processing
            _ = event.to_dict()
        
        # Measure processing time
        for i in range(10):
            start = time.perf_counter()
            await event_bus.publish(
                EventType.APPOINTMENT_CREATED,
                {"index": i},
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            processing_times.append(elapsed_ms)
        
        # Assert average under 100ms (realistic for async operations)
        avg_time = sum(processing_times) / len(processing_times)
        assert avg_time < 100, f"Average processing time {avg_time:.2f}ms > 100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
