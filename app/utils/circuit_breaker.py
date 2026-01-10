"""
Circuit Breaker pattern implementation for Nexus Miracle.
Protects services from cascading failures.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 30.0  # Seconds before testing recovery
    half_open_max_calls: int = 3  # Max calls in half-open state
    
    # Arabic fallback messages for each service
    fallback_messages: dict[str, str] = field(default_factory=lambda: {
        "asr": "عذراً، ما سمعتك زين. ممكن تعيد؟",
        "llm": "النظام مشغول، لحظة وأرجع لك",
        "tts": "عذراً، في مشكلة تقنية. حاول مرة ثانية",
        "default": "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى",
    })


class CircuitBreaker:
    """
    Circuit Breaker implementation for service protection.
    
    Usage:
        breaker = CircuitBreaker("llm_service")
        
        @breaker.protect
        async def call_llm(prompt: str) -> str:
            return await llm_client.generate(prompt)
        
        # Or manual usage:
        try:
            result = await breaker.call(call_llm, prompt)
        except CircuitBreakerOpen:
            # Handle fallback
    """
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0
        
        logger.info(f"CircuitBreaker '{name}' initialized (threshold={self.config.failure_threshold})")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self._last_failure_time >= self.config.recovery_timeout:
                logger.info(f"CircuitBreaker '{self.name}' transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        
        return self._state
    
    @property
    def is_available(self) -> bool:
        """Check if the circuit breaker allows requests."""
        return self.state != CircuitState.OPEN
    
    def get_fallback_message(self, service_type: str = "default") -> str:
        """Get Arabic fallback message for the service."""
        return self.config.fallback_messages.get(
            service_type,
            self.config.fallback_messages["default"]
        )
    
    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.half_open_max_calls:
                logger.info(f"CircuitBreaker '{self.name}' recovered, transitioning to CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def record_failure(self, error: Exception | None = None) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        logger.warning(
            f"CircuitBreaker '{self.name}' recorded failure #{self._failure_count}: {error}"
        )
        
        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery test, re-open
            logger.warning(f"CircuitBreaker '{self.name}' failed during recovery, re-opening")
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.config.failure_threshold:
            logger.error(f"CircuitBreaker '{self.name}' threshold reached, opening circuit")
            self._state = CircuitState.OPEN
    
    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                self.name,
                self.get_fallback_message(self.name),
            )
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls > self.config.half_open_max_calls:
                raise CircuitBreakerOpen(
                    self.name,
                    self.get_fallback_message(self.name),
                )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise
    
    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with the circuit breaker."""
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info(f"CircuitBreaker '{self.name}' reset to CLOSED")
    
    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, fallback_message: str) -> None:
        self.service_name = service_name
        self.fallback_message = fallback_message
        super().__init__(f"Circuit breaker '{service_name}' is open")


# Pre-configured circuit breakers for each service
class CircuitBreakers:
    """Container for all circuit breakers."""
    
    asr = CircuitBreaker("asr", CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=20.0,
        fallback_messages={
            "asr": "عذراً، ما سمعتك زين. ممكن تعيد؟",
            "default": "عذراً، ما سمعتك زين. ممكن تعيد؟",
        }
    ))
    
    llm = CircuitBreaker("llm", CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        fallback_messages={
            "llm": "النظام مشغول، لحظة وأرجع لك",
            "default": "النظام مشغول، لحظة وأرجع لك",
        }
    ))
    
    tts = CircuitBreaker("tts", CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=20.0,
        fallback_messages={
            "tts": "عذراً، في مشكلة تقنية. حاول مرة ثانية",
            "default": "عذراً، في مشكلة تقنية. حاول مرة ثانية",
        }
    ))
    
    @classmethod
    def get_all_stats(cls) -> dict[str, dict]:
        """Get stats for all circuit breakers."""
        return {
            "asr": cls.asr.get_stats(),
            "llm": cls.llm.get_stats(),
            "tts": cls.tts.get_stats(),
        }
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        cls.asr.reset()
        cls.llm.reset()
        cls.tts.reset()
