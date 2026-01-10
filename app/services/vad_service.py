"""
Nexus Miracle - VAD Service

Silero VAD integration for voice activity detection.
Detects speech segments in real-time audio streams.
Target: <5ms per chunk processing.
"""

from enum import Enum
from typing import Any

import numpy as np
from loguru import logger

from app.config import get_settings
from app.exceptions import VADException, VADInitializationError


class VADEvent(str, Enum):
    """VAD state events."""
    
    SPEECH_START = "speech_start"
    SPEECH_CONTINUE = "speech_continue"
    SPEECH_END = "speech_end"
    SILENCE = "silence"


class VADService:
    """
    Voice Activity Detection service using Silero VAD.
    
    Provides real-time speech detection for:
    - Determining when user is speaking
    - Detecting end of speech for response triggering
    - Filtering non-speech audio
    
    Target latency: <5ms per audio chunk.
    """
    
    def __init__(self) -> None:
        """Initialize the VAD service."""
        self._settings = get_settings()
        self._model: Any = None
        self._vad_iterator: Any = None
        self._is_initialized = False
        
        # VAD configuration
        self._sample_rate = 16000  # Silero expects 16kHz
        self._threshold = self._settings.vad_threshold
        self._min_silence_ms = self._settings.vad_min_silence_ms
        self._min_speech_ms = 250  # Minimum speech duration
        
        # Tracking state
        self._is_speaking = False
        self._speech_start_sample = 0
        self._silence_samples = 0
        self._speech_samples = 0
        self._total_samples_processed = 0
        
        # Audio buffer for processing
        self._audio_buffer: list[np.ndarray] = []
        self._buffer_samples = 0
        
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
            import torch
            
            # Load Silero VAD model
            self._model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True,
            )
            self._model.eval()
            
            # Get helper functions
            self._get_speech_timestamps = utils[0]
            
            # Create VAD iterator for streaming
            from silero_vad import VADIterator
            self._vad_iterator = VADIterator(
                self._model,
                threshold=self._threshold,
                sampling_rate=self._sample_rate,
                min_silence_duration_ms=self._min_silence_ms,
                speech_pad_ms=30,
            )
            
            self._is_initialized = True
            logger.info(
                f"VADService initialized: threshold={self._threshold}, "
                f"min_silence={self._min_silence_ms}ms"
            )
            
        except ImportError as e:
            # Fallback to energy-based VAD if Silero not available
            logger.warning(f"Silero VAD not available, using energy-based fallback: {e}")
            self._is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize VAD service: {e}")
            raise VADInitializationError(
                message="Failed to initialize VAD model",
                details={"error": str(e)},
            )
    
    def reset(self) -> None:
        """Reset VAD state for new audio stream."""
        self._is_speaking = False
        self._speech_start_sample = 0
        self._silence_samples = 0
        self._speech_samples = 0
        self._total_samples_processed = 0
        self._audio_buffer.clear()
        self._buffer_samples = 0
        
        if self._vad_iterator:
            self._vad_iterator.reset_states()
        
        logger.debug("VAD state reset")
    
    def process_chunk(self, audio_chunk: bytes | np.ndarray) -> VADEvent:
        """
        Process a single audio chunk and return VAD event.
        
        Args:
            audio_chunk: Raw audio bytes (16-bit PCM) or numpy array
        
        Returns:
            VADEvent indicating the current speech state
        """
        # Convert to numpy if needed
        if isinstance(audio_chunk, bytes):
            audio = np.frombuffer(audio_chunk, dtype=np.int16)
        else:
            audio = audio_chunk
        
        # Convert to float32 normalized
        audio_float = audio.astype(np.float32) / 32768.0
        
        # Get speech probability
        speech_prob = self._get_speech_probability(audio_float)
        is_speech = speech_prob >= self._threshold
        
        # Update sample counts
        chunk_samples = len(audio_float)
        self._total_samples_processed += chunk_samples
        
        # State machine
        if is_speech:
            self._speech_samples += chunk_samples
            self._silence_samples = 0
            
            if not self._is_speaking:
                # Speech started
                self._is_speaking = True
                self._speech_start_sample = self._total_samples_processed
                logger.debug(f"Speech started (prob={speech_prob:.2f})")
                return VADEvent.SPEECH_START
            else:
                return VADEvent.SPEECH_CONTINUE
        else:
            self._silence_samples += chunk_samples
            
            if self._is_speaking:
                # Check if silence exceeds threshold
                silence_ms = (self._silence_samples / self._sample_rate) * 1000
                
                if silence_ms >= self._min_silence_ms:
                    # Speech ended
                    self._is_speaking = False
                    speech_duration_ms = (self._speech_samples / self._sample_rate) * 1000
                    
                    logger.debug(
                        f"Speech ended: duration={speech_duration_ms:.0f}ms, "
                        f"silence={silence_ms:.0f}ms"
                    )
                    
                    # Reset speech counter
                    self._speech_samples = 0
                    return VADEvent.SPEECH_END
                else:
                    # Still in speech, just a short pause
                    return VADEvent.SPEECH_CONTINUE
            
            return VADEvent.SILENCE
    
    def _get_speech_probability(self, audio_float: np.ndarray) -> float:
        """
        Get speech probability for audio chunk.
        
        Args:
            audio_float: Float32 audio array (-1 to 1)
        
        Returns:
            Speech probability (0 to 1)
        """
        if self._model is not None:
            try:
                import torch
                
                # Ensure correct sample count (512 samples = 32ms at 16kHz)
                audio_tensor = torch.from_numpy(audio_float)
                
                with torch.no_grad():
                    speech_prob = self._model(audio_tensor, self._sample_rate).item()
                
                return speech_prob
                
            except Exception as e:
                logger.warning(f"Silero VAD inference failed: {e}")
        
        # Fallback: energy-based detection
        energy = np.sqrt(np.mean(audio_float ** 2))
        # Convert RMS to pseudo-probability
        speech_prob = min(energy * 10, 1.0)
        return speech_prob
    
    async def process_audio(self, audio_bytes: bytes) -> dict[str, Any]:
        """
        Process an audio chunk and return VAD results.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
        
        Returns:
            VAD result with speech probability and state
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            # Get event
            event = self.process_chunk(audio_bytes)
            
            # Compute metrics
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio.astype(np.float32) / 32768.0
            speech_prob = self._get_speech_probability(audio_float)
            
            return {
                "event": event,
                "speech_probability": speech_prob,
                "is_speech": event in (VADEvent.SPEECH_START, VADEvent.SPEECH_CONTINUE),
                "is_speaking": self._is_speaking,
                "speech_ended": event == VADEvent.SPEECH_END,
                "silence_ms": (self._silence_samples / self._sample_rate) * 1000,
                "speech_ms": (self._speech_samples / self._sample_rate) * 1000,
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
    
    async def detect_end_of_speech(self, audio_bytes: bytes) -> bool:
        """
        Detect if speech has ended.
        
        Args:
            audio_bytes: Raw audio bytes
        
        Returns:
            True if speech has ended, False otherwise
        """
        result = await self.process_audio(audio_bytes)
        return result["speech_ended"]
    
    def get_current_state(self) -> dict[str, Any]:
        """Get current VAD state."""
        return {
            "is_speaking": self._is_speaking,
            "speech_samples": self._speech_samples,
            "silence_samples": self._silence_samples,
            "silence_ms": (self._silence_samples / self._sample_rate) * 1000,
            "total_processed": self._total_samples_processed,
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._model = None
        self._vad_iterator = None
        self.reset()
        logger.info("VADService shutdown")


# Singleton instance
_vad_service: VADService | None = None


def get_vad_service() -> VADService:
    """Get the VAD service singleton instance."""
    global _vad_service
    if _vad_service is None:
        _vad_service = VADService()
    return _vad_service
