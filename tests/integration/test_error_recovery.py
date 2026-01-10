"""
Integration test for error recovery.
Tests: Circuit breaker, fallback messages, graceful degradation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

import sys
sys.path.insert(0, ".")


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.fixture
    def breaker(self):
        """Create fresh circuit breaker."""
        from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
        )
        return CircuitBreaker("test_service", config)
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self, breaker):
        """Test that circuit opens after consecutive failures."""
        from app.utils.circuit_breaker import CircuitState, CircuitBreakerOpen
        
        async def failing_function():
            raise Exception("Service unavailable")
        
        # Trigger failures up to threshold
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_function)
        
        # Circuit should be open now
        assert breaker.state == CircuitState.OPEN
        
        # Next call should raise CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await breaker.call(failing_function)
        
        assert exc_info.value.service_name == "test_service"
    
    @pytest.mark.asyncio
    async def test_circuit_recovers_after_timeout(self, breaker):
        """Test that circuit transitions to half-open after timeout."""
        from app.utils.circuit_breaker import CircuitState
        import time
        
        async def failing_function():
            raise Exception("Service unavailable")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_function)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Circuit should be half-open
        assert breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_successful_calls_close_circuit(self, breaker):
        """Test that successful calls close the circuit."""
        from app.utils.circuit_breaker import CircuitState
        
        call_count = 0
        
        async def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Fail")
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(sometimes_failing_function)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery
        await asyncio.sleep(1.1)
        
        # Successful call should close circuit
        result = await breaker.call(sometimes_failing_function)
        assert result == "success"
        
        # More successful calls to fully close
        for _ in range(2):
            await breaker.call(sometimes_failing_function)
        
        assert breaker.state == CircuitState.CLOSED
    
    def test_fallback_messages_are_arabic(self, breaker):
        """Test that fallback messages are in Arabic."""
        from app.utils.circuit_breaker import CircuitBreakerConfig
        
        config = CircuitBreakerConfig()
        
        # All fallback messages should contain Arabic
        for key, message in config.fallback_messages.items():
            # Check for Arabic characters
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in message)
            assert has_arabic, f"Message for '{key}' should be in Arabic"


class TestServiceFallbacks:
    """Test service-specific fallback handling."""
    
    @pytest.mark.asyncio
    async def test_asr_fallback_on_failure(self):
        """Test ASR service returns fallback on failure."""
        from app.utils.circuit_breaker import CircuitBreakers, CircuitBreakerOpen
        
        # Reset for clean test
        CircuitBreakers.asr.reset()
        
        async def mock_asr():
            raise Exception("ElevenLabs API error")
        
        # Trigger failures
        for _ in range(3):
            with pytest.raises(Exception):
                await CircuitBreakers.asr.call(mock_asr)
        
        # Get fallback message
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await CircuitBreakers.asr.call(mock_asr)
        
        fallback = exc_info.value.fallback_message
        assert "ما سمعتك" in fallback or "عذراً" in fallback
    
    @pytest.mark.asyncio
    async def test_llm_fallback_on_timeout(self):
        """Test LLM service returns fallback on timeout."""
        from app.utils.circuit_breaker import CircuitBreakers, CircuitBreakerOpen
        
        CircuitBreakers.llm.reset()
        
        async def mock_llm():
            raise asyncio.TimeoutError("LLM timeout")
        
        # Trigger failures
        for _ in range(5):
            with pytest.raises(asyncio.TimeoutError):
                await CircuitBreakers.llm.call(mock_llm)
        
        # Get fallback
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await CircuitBreakers.llm.call(mock_llm)
        
        fallback = exc_info.value.fallback_message
        assert "مشغول" in fallback or "لحظة" in fallback
    
    @pytest.mark.asyncio
    async def test_tts_fallback_on_failure(self):
        """Test TTS service returns fallback on failure."""
        from app.utils.circuit_breaker import CircuitBreakers, CircuitBreakerOpen
        
        CircuitBreakers.tts.reset()
        
        async def mock_tts():
            raise Exception("TTS API error")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await CircuitBreakers.tts.call(mock_tts)
        
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await CircuitBreakers.tts.call(mock_tts)
        
        fallback = exc_info.value.fallback_message
        assert "مشكلة" in fallback or "عذراً" in fallback


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""
    
    @pytest.mark.asyncio
    async def test_partial_service_failure_handling(self):
        """Test system continues when one service fails."""
        from app.utils.circuit_breaker import CircuitBreakers, CircuitBreakerOpen
        
        # Reset all breakers
        CircuitBreakers.reset_all()
        
        # Simulate TTS failure but ASR working
        async def mock_asr():
            return "transcribed text"
        
        async def mock_tts():
            raise Exception("TTS failed")
        
        # ASR should work
        result = await CircuitBreakers.asr.call(mock_asr)
        assert result == "transcribed text"
        
        # TTS fails but system should handle gracefully
        for _ in range(3):
            with pytest.raises(Exception):
                await CircuitBreakers.tts.call(mock_tts)
        
        # TTS is now open, but ASR still works
        result = await CircuitBreakers.asr.call(mock_asr)
        assert result == "transcribed text"
        
        # TTS returns fallback
        with pytest.raises(CircuitBreakerOpen):
            await CircuitBreakers.tts.call(mock_tts)
    
    @pytest.mark.asyncio
    async def test_call_continues_after_single_failure(self):
        """Test that a single failure doesn't crash the call."""
        from app.utils.circuit_breaker import CircuitBreakers
        
        CircuitBreakers.reset_all()
        
        fail_count = 0
        
        async def sometimes_failing():
            nonlocal fail_count
            fail_count += 1
            if fail_count == 1:
                raise Exception("Temporary failure")
            return "success"
        
        # First call fails
        with pytest.raises(Exception):
            await CircuitBreakers.llm.call(sometimes_failing)
        
        # Circuit still closed (threshold not reached)
        assert CircuitBreakers.llm.is_available
        
        # Second call succeeds
        result = await CircuitBreakers.llm.call(sometimes_failing)
        assert result == "success"


class TestMetricsOnError:
    """Test that errors are properly recorded in metrics."""
    
    @pytest.mark.asyncio
    async def test_error_increments_counter(self):
        """Test that errors increment the error counter."""
        from app.utils.monitoring import metrics
        
        initial_count = metrics._error_count
        
        metrics.increment_error_count("test_error")
        
        assert metrics._error_count == initial_count + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
