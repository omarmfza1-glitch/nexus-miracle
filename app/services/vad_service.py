"""
Nexus Miracle - VAD Service

Silero VAD integration for voice activity detection.
Detects speech segments in real-time audio streams.
"""

from typing import Any

import numpy as np
from loguru import logger

from app.config import get_settings
from app.exceptions import VADException, VADInitializationError


class VADService:
    """
    Voice Activity Detection service using Silero VAD.
    
    Provides real-time speech detection for:
    - Determining when user is speaking
    - Detecting end of speech for response triggering
    - Filtering non-speech audio
    """
    
    def __init__(self) -> None:
        """Initialize the VAD service."""
        self._settings = get_settings()
        self._model: Any = None
        self._is_initialized = False
        
        # VAD state
        self._sample_rate = self._settings.audio_sample_rate
        self._threshold = self._settings.vad_threshold
        self._min_silence_ms = self._settings.vad_min_silence_ms
        
        # Tracking state
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_samples = 0
        
        logger.info("VADService created")
    
    async def initialize(self) -> None:
        """
        Initialize the Silero VAD model.
        
        Raises:
            VADInitializationError: If model loading fails
        """
        if self._is_initialized:
            return
        
        try:
            # TODO: Load Silero VAD model
            # import torch
            # self._model, utils = torch.hub.load(
            #     repo_or_dir='snakers4/silero-vad',
            #     model='silero_vad',
            #     force_reload=False,
            # )
            # self._model.eval()
            
            self._is_initialized = True
            logger.info(
                f"VADService initialized: threshold={self._threshold}, "
                f"min_silence={self._min_silence_ms}ms"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize VAD service: {e}")
            raise VADInitializationError(
                message="Failed to initialize VAD model",
                details={"error": str(e)},
            )
    
    def reset_state(self) -> None:
        """Reset VAD tracking state for new audio stream."""
        self._is_speaking = False
        self._silence_samples = 0
        self._speech_samples = 0
        logger.debug("VAD state reset")
    
    async def process_audio(
        self,
        audio_bytes: bytes,
    ) -> dict[str, Any]:
        """
        Process an audio chunk and return VAD results.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
        
        Returns:
            VAD result with speech probability and state
        
        Raises:
            VADException: If processing fails
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # TODO: Run VAD inference
            # with torch.no_grad():
            #     speech_prob = self._model(
            #         torch.from_numpy(audio_float),
            #         self._sample_rate
            #     ).item()
            
            # Placeholder - simulate speech detection
            speech_prob = 0.0
            if len(audio_float) > 0:
                # Simple energy-based placeholder
                energy = np.mean(np.abs(audio_float))
                speech_prob = min(energy * 100, 1.0)
            
            # Update state
            is_speech = speech_prob >= self._threshold
            
            if is_speech:
                self._speech_samples += len(audio_float)
                self._silence_samples = 0
                
                if not self._is_speaking:
                    self._is_speaking = True
                    logger.debug("Speech started")
            else:
                self._silence_samples += len(audio_float)
                
                # Check if silence exceeds threshold
                silence_ms = (self._silence_samples / self._sample_rate) * 1000
                
                if self._is_speaking and silence_ms >= self._min_silence_ms:
                    self._is_speaking = False
                    speech_duration_ms = (self._speech_samples / self._sample_rate) * 1000
                    logger.debug(f"Speech ended after {speech_duration_ms:.0f}ms")
                    self._speech_samples = 0
            
            return {
                "speech_probability": speech_prob,
                "is_speech": is_speech,
                "is_speaking": self._is_speaking,
                "speech_ended": not self._is_speaking and self._speech_samples == 0,
                "silence_ms": (self._silence_samples / self._sample_rate) * 1000,
            }
            
        except Exception as e:
            logger.error(f"VAD processing failed: {e}")
            raise VADException(
                message="Voice activity detection failed",
                details={"error": str(e)},
            )
    
    async def is_speech(self, audio_bytes: bytes) -> bool:
        """
        Quick check if audio contains speech.
        
        Args:
            audio_bytes: Raw audio bytes
        
        Returns:
            True if speech detected, False otherwise
        """
        result = await self.process_audio(audio_bytes)
        return result["is_speech"]
    
    async def detect_end_of_speech(
        self,
        audio_bytes: bytes,
    ) -> bool:
        """
        Detect if the current audio marks end of speech.
        
        Used to trigger response generation when user
        stops speaking.
        
        Args:
            audio_bytes: Raw audio bytes
        
        Returns:
            True if speech has ended, False otherwise
        """
        result = await self.process_audio(audio_bytes)
        
        # End of speech when:
        # 1. Was speaking before
        # 2. Currently not speaking
        # 3. Silence exceeds threshold
        return (
            not result["is_speaking"] and 
            result["silence_ms"] >= self._min_silence_ms
        )
    
    def get_current_state(self) -> dict[str, Any]:
        """
        Get current VAD state.
        
        Returns:
            Current state information
        """
        return {
            "is_speaking": self._is_speaking,
            "speech_samples": self._speech_samples,
            "silence_samples": self._silence_samples,
            "silence_ms": (self._silence_samples / self._sample_rate) * 1000,
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._model = None
        self.reset_state()
        logger.info("VADService shutdown")


# Singleton instance
_vad_service: VADService | None = None


def get_vad_service() -> VADService:
    """
    Get the VAD service singleton instance.
    
    Returns:
        VADService instance
    """
    global _vad_service
    if _vad_service is None:
        _vad_service = VADService()
    return _vad_service
