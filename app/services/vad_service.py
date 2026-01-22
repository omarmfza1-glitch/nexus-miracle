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
        
        # Import runtime settings for dynamic configuration
        from app.services.runtime_settings import get_runtime_settings
        self._runtime_settings = get_runtime_settings()
        
        # VAD configuration - now read dynamically from RuntimeSettings
        self._sample_rate = 16000  # Silero expects 16kHz
        
        # Tracking state
        self._is_speaking = False
        self._speech_start_sample = 0
        self._silence_samples = 0
        self._speech_samples = 0
        self._total_samples_processed = 0
        
        # Audio buffer for processing
        self._audio_buffer: list[np.ndarray] = []
        self._buffer_samples = 0
        
        logger.info("VADService created with dynamic settings")
    
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
        
        # Use direct energy-based detection (more reliable for web audio)
        energy_rms = np.sqrt(np.mean(audio_float ** 2))
        speech_prob = min(energy_rms * 15, 1.0)  # Same multiplier as in process_audio
        
        # Read threshold dynamically from RuntimeSettings
        threshold = self._runtime_settings.vad_threshold
        is_speech = speech_prob >= threshold
        
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
                logger.info(f"🎙️ Speech started (prob={speech_prob:.2f}, energy={energy_rms:.4f})")
                return VADEvent.SPEECH_START
            else:
                return VADEvent.SPEECH_CONTINUE
        else:
            self._silence_samples += chunk_samples
            
            if self._is_speaking:
                # Check if silence exceeds threshold - read dynamically
                silence_ms = (self._silence_samples / self._sample_rate) * 1000
                speech_duration_ms = (self._speech_samples / self._sample_rate) * 1000
                
                # Get thresholds from RuntimeSettings
                min_silence_ms = self._runtime_settings.vad_min_silence_ms
                min_speech_ms = self._runtime_settings.vad_min_speech_ms
                
                if silence_ms >= min_silence_ms:
                    # Check if we have enough speech before ending
                    if speech_duration_ms >= min_speech_ms:
                        # Speech ended with sufficient duration
                        self._is_speaking = False
                        
                        logger.info(
                            f"Speech ended: duration={speech_duration_ms:.0f}ms, "
                            f"silence={silence_ms:.0f}ms"
                        )
                        
                        # Reset speech counter
                        self._speech_samples = 0
                        return VADEvent.SPEECH_END
                    else:
                        # Too short, treat as noise and reset
                        logger.debug(
                            f"Speech too short ({speech_duration_ms:.0f}ms < {min_speech_ms}ms), ignoring"
                        )
                        self._is_speaking = False
                        self._speech_samples = 0
                        return VADEvent.SILENCE
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
        # Silero VAD requires minimum 512 samples (32ms at 16kHz)
        MIN_SAMPLES = 512
        
        # Add to buffer
        self._audio_buffer.append(audio_float)
        self._buffer_samples += len(audio_float)
        
        # If not enough samples yet, use energy-based fallback
        if self._buffer_samples < MIN_SAMPLES:
            energy = np.sqrt(np.mean(audio_float ** 2))
            return min(energy * 10, 1.0)
        
        # Concatenate buffer
        buffered_audio = np.concatenate(self._audio_buffer)
        
        # Clear buffer but keep overflow
        if len(buffered_audio) > MIN_SAMPLES:
            # Keep samples beyond MIN_SAMPLES for next iteration
            overflow = buffered_audio[MIN_SAMPLES:]
            self._audio_buffer = [overflow] if len(overflow) > 0 else []
            self._buffer_samples = len(overflow) if len(overflow) > 0 else 0
            buffered_audio = buffered_audio[:MIN_SAMPLES]
        else:
            self._audio_buffer = []
            self._buffer_samples = 0
        
        if self._model is not None:
            try:
                import torch
                
                audio_tensor = torch.from_numpy(buffered_audio)
                
                with torch.no_grad():
                    speech_prob = self._model(audio_tensor, self._sample_rate).item()
                
                return speech_prob
                
            except Exception as e:
                logger.warning(f"Silero VAD inference failed: {e}")
        
        # Fallback: energy-based detection
        energy = np.sqrt(np.mean(buffered_audio ** 2))
        # Convert RMS to pseudo-probability (increased multiplier for better web audio sensitivity)
        speech_prob = min(energy * 15, 1.0)
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
            # Calculate energy for logging
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio.astype(np.float32) / 32768.0
            energy_rms = np.sqrt(np.mean(audio_float ** 2))
            
            # Get event (this internally calculates speech_prob)
            event = self.process_chunk(audio_bytes)
            
            # Get the last calculated speech probability from the internal state
            # Use energy-based calculation for reporting
            speech_prob = min(energy_rms * 15, 1.0)  # Increased multiplier for better sensitivity
            
            # Log every few chunks for debugging (when there's some energy)
            if energy_rms > 0.01:
                logger.debug(f"VAD chunk: energy_rms={energy_rms:.4f}, prob={speech_prob:.2f}, speaking={self._is_speaking}, event={event}")
            
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
