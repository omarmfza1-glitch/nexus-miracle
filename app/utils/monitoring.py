"""
Monitoring and metrics collection for Nexus Miracle.
Provides structured logging, timing decorators, and metrics.
"""

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TypeVar
import json

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: dict[str, str] = field(default_factory=dict)


class Metrics:
    """
    Metrics collection for the application.
    
    Collects:
    - Latency histograms (VAD, ASR, LLM, TTS)
    - Counters (calls, errors)
    - Gauges (active calls)
    """
    
    _instance: "Metrics | None" = None
    
    def __new__(cls) -> "Metrics":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        # Counters
        self._call_count = 0
        self._error_count = 0
        self._appointment_count = 0
        
        # Gauges
        self._active_calls = 0
        
        # Histograms (store recent values)
        self._latencies: dict[str, list[float]] = {
            "vad": [],
            "asr": [],
            "llm_ttft": [],
            "llm_total": [],
            "tts_ttfb": [],
            "tts_total": [],
            "end_to_end": [],
        }
        self._max_samples = 100
        
        self._initialized = True
        logger.info("Metrics collector initialized")
    
    # Counters
    def increment_call_count(self) -> None:
        self._call_count += 1
    
    def increment_error_count(self, error_type: str = "unknown") -> None:
        self._error_count += 1
        logger.warning(f"Error recorded: {error_type}")
    
    def increment_appointment_count(self) -> None:
        self._appointment_count += 1
    
    # Gauges
    def set_active_calls(self, count: int) -> None:
        self._active_calls = count
    
    def increment_active_calls(self) -> None:
        self._active_calls += 1
    
    def decrement_active_calls(self) -> None:
        self._active_calls = max(0, self._active_calls - 1)
    
    # Histograms
    def record_latency(self, service: str, latency_ms: float) -> None:
        """Record a latency measurement."""
        if service in self._latencies:
            self._latencies[service].append(latency_ms)
            # Keep only recent samples
            if len(self._latencies[service]) > self._max_samples:
                self._latencies[service].pop(0)
            
            logger.debug(f"Latency recorded: {service}={latency_ms:.2f}ms")
    
    def get_latency_stats(self, service: str) -> dict[str, float]:
        """Get latency statistics for a service."""
        values = self._latencies.get(service, [])
        if not values:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "avg": sum(values) / count,
            "min": min(values),
            "max": max(values),
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)] if count >= 20 else sorted_values[-1],
            "p99": sorted_values[int(count * 0.99)] if count >= 100 else sorted_values[-1],
        }
    
    def get_all_stats(self) -> dict[str, Any]:
        """Get all metrics statistics."""
        return {
            "counters": {
                "call_count": self._call_count,
                "error_count": self._error_count,
                "appointment_count": self._appointment_count,
            },
            "gauges": {
                "active_calls": self._active_calls,
            },
            "latencies": {
                service: self.get_latency_stats(service)
                for service in self._latencies
            },
            "timestamp": datetime.now().isoformat(),
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._call_count = 0
        self._error_count = 0
        self._appointment_count = 0
        self._active_calls = 0
        for key in self._latencies:
            self._latencies[key] = []


# Global metrics instance
metrics = Metrics()


def timed(service: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to measure and record function execution time.
    
    Usage:
        @timed("llm")
        async def generate_response(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                metrics.record_latency(service, elapsed_ms)
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                metrics.record_latency(service, elapsed_ms)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


@contextmanager
def measure_latency(service: str):
    """
    Context manager to measure latency.
    
    Usage:
        with measure_latency("llm"):
            result = await call_llm()
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        metrics.record_latency(service, elapsed_ms)


class StructuredLogger:
    """
    Structured JSON logging for production.
    
    Usage:
        log = StructuredLogger("call_handler")
        log.info("Call started", call_id="abc123", patient="عمر")
    """
    
    def __init__(self, service: str) -> None:
        self.service = service
        self.logger = logging.getLogger(service)
    
    def _format(self, level: str, message: str, **kwargs: Any) -> str:
        """Format log entry as JSON."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "service": self.service,
            "message": message,
            **kwargs,
        }
        return json.dumps(entry, ensure_ascii=False)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(self._format("DEBUG", message, **kwargs))
    
    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(self._format("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(self._format("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(self._format("ERROR", message, **kwargs))
    
    def critical(self, message: str, **kwargs: Any) -> None:
        self.logger.critical(self._format("CRITICAL", message, **kwargs))
