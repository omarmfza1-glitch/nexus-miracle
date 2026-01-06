"""
Nexus Miracle - Custom Exceptions

Application-specific exception classes for proper error handling.
"""

from typing import Any


class NexusMiracleException(Exception):
    """Base exception for all Nexus Miracle errors."""
    
    def __init__(
        self,
        message: str = "An unexpected error occurred",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ===========================================
# Telephony Exceptions
# ===========================================

class TelephonyException(NexusMiracleException):
    """Base exception for telephony-related errors."""
    pass


class CallConnectionError(TelephonyException):
    """Raised when a call connection fails."""
    pass


class WebhookValidationError(TelephonyException):
    """Raised when webhook validation fails."""
    pass


class WebSocketConnectionError(TelephonyException):
    """Raised when WebSocket connection fails."""
    pass


# ===========================================
# ASR Exceptions
# ===========================================

class ASRException(NexusMiracleException):
    """Base exception for ASR-related errors."""
    pass


class TranscriptionError(ASRException):
    """Raised when speech transcription fails."""
    pass


# ===========================================
# LLM Exceptions
# ===========================================

class LLMException(NexusMiracleException):
    """Base exception for LLM-related errors."""
    pass


class GenerationError(LLMException):
    """Raised when text generation fails."""
    pass


class ContextLimitExceeded(LLMException):
    """Raised when conversation context exceeds limits."""
    pass


# ===========================================
# TTS Exceptions
# ===========================================

class TTSException(NexusMiracleException):
    """Base exception for TTS-related errors."""
    pass


class SynthesisError(TTSException):
    """Raised when speech synthesis fails."""
    pass


class VoiceNotFoundError(TTSException):
    """Raised when requested voice is not available."""
    pass


# ===========================================
# VAD Exceptions
# ===========================================

class VADException(NexusMiracleException):
    """Base exception for VAD-related errors."""
    pass


class VADInitializationError(VADException):
    """Raised when VAD model initialization fails."""
    pass


# ===========================================
# Configuration Exceptions
# ===========================================

class ConfigurationError(NexusMiracleException):
    """Raised when configuration is invalid."""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Raised when required API key is missing."""
    pass


# ===========================================
# Appointment Exceptions
# ===========================================

class AppointmentException(NexusMiracleException):
    """Base exception for appointment-related errors."""
    pass


class AppointmentNotFoundError(AppointmentException):
    """Raised when appointment is not found."""
    pass


class AppointmentConflictError(AppointmentException):
    """Raised when there's a scheduling conflict."""
    pass
