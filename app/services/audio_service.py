"""
Nexus Miracle - Audio Processing Service

Handles audio codec conversions and resampling for Telnyx integration.
Converts between μ-law 8kHz (Telnyx) and PCM 16kHz (AI services).
"""

import audioop
import struct
from typing import Optional

import numpy as np
from loguru import logger

try:
    from scipy.signal import resample_poly
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available, using numpy for resampling")


class AudioProcessor:
    """
    Audio codec and resampling processor.
    
    Handles:
    - μ-law to PCM conversion (Telnyx inbound)
    - PCM to μ-law conversion (Telnyx outbound)
    - Resampling between 8kHz and 16kHz
    """
    
    # Audio constants
    TELNYX_SAMPLE_RATE = 8000   # Telnyx uses 8kHz
    AI_SAMPLE_RATE = 16000      # AI services use 16kHz
    CHUNK_DURATION_MS = 20      # 20ms chunks
    
    # Samples per chunk at each rate
    SAMPLES_8K_20MS = 160       # 8000 * 0.020 = 160 samples
    SAMPLES_16K_20MS = 320      # 16000 * 0.020 = 320 samples
    
    def __init__(self) -> None:
        """Initialize the audio processor."""
        logger.info("AudioProcessor created")
    
    def ulaw_to_pcm(self, ulaw_bytes: bytes) -> np.ndarray:
        """
        Convert μ-law encoded audio to PCM samples.
        
        Args:
            ulaw_bytes: μ-law encoded audio bytes
        
        Returns:
            PCM samples as int16 numpy array
        """
        try:
            # Use audioop for μ-law decoding
            pcm_bytes = audioop.ulaw2lin(ulaw_bytes, 2)  # 2 = 16-bit
            
            # Convert to numpy array
            pcm_array = np.frombuffer(pcm_bytes, dtype=np.int16)
            
            return pcm_array
            
        except Exception as e:
            logger.error(f"μ-law to PCM conversion failed: {e}")
            raise
    
    def pcm_to_ulaw(self, pcm_array: np.ndarray) -> bytes:
        """
        Convert PCM samples to μ-law encoded audio.
        
        Args:
            pcm_array: PCM samples as int16 or float32 numpy array
        
        Returns:
            μ-law encoded audio bytes
        """
        try:
            # Ensure int16 format
            if pcm_array.dtype == np.float32 or pcm_array.dtype == np.float64:
                # Scale from [-1, 1] to int16 range
                pcm_array = (pcm_array * 32767).astype(np.int16)
            elif pcm_array.dtype != np.int16:
                pcm_array = pcm_array.astype(np.int16)
            
            # Convert to bytes
            pcm_bytes = pcm_array.tobytes()
            
            # Use audioop for μ-law encoding
            ulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)  # 2 = 16-bit
            
            return ulaw_bytes
            
        except Exception as e:
            logger.error(f"PCM to μ-law conversion failed: {e}")
            raise
    
    def resample(
        self,
        audio: np.ndarray,
        from_rate: int,
        to_rate: int,
    ) -> np.ndarray:
        """
        Resample audio from one sample rate to another.
        
        Args:
            audio: Audio samples as numpy array
            from_rate: Original sample rate
            to_rate: Target sample rate
        
        Returns:
            Resampled audio as numpy array
        """
        if from_rate == to_rate:
            return audio
        
        try:
            if SCIPY_AVAILABLE:
                # Use scipy for high-quality resampling
                # Find GCD for optimal up/down factors
                from math import gcd
                g = gcd(from_rate, to_rate)
                up = to_rate // g
                down = from_rate // g
                
                resampled = resample_poly(audio.astype(np.float64), up, down)
                
                # Preserve dtype
                if audio.dtype == np.int16:
                    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
                
                return resampled
            else:
                # Fallback to numpy linear interpolation
                num_samples = int(len(audio) * to_rate / from_rate)
                indices = np.linspace(0, len(audio) - 1, num_samples)
                resampled = np.interp(indices, np.arange(len(audio)), audio)
                
                if audio.dtype == np.int16:
                    resampled = resampled.astype(np.int16)
                
                return resampled
                
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            raise
    
    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to [-1, 1] range.
        
        Args:
            audio: Audio samples as numpy array
        
        Returns:
            Normalized audio as float32 numpy array
        """
        if audio.dtype == np.int16:
            return audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.float32 or audio.dtype == np.float64:
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                return (audio / max_val).astype(np.float32)
            return audio.astype(np.float32)
        else:
            return audio.astype(np.float32)
    
    def telnyx_to_ai(self, ulaw_8k: bytes) -> bytes:
        """
        Convert Telnyx audio format to AI services format.
        
        Telnyx: μ-law encoded, 8kHz
        AI: PCM 16-bit, 16kHz
        
        Args:
            ulaw_8k: μ-law encoded 8kHz audio bytes
        
        Returns:
            PCM 16-bit 16kHz audio bytes
        """
        # Decode μ-law to PCM
        pcm_8k = self.ulaw_to_pcm(ulaw_8k)
        
        # Resample 8kHz to 16kHz
        pcm_16k = self.resample(pcm_8k, 8000, 16000)
        
        return pcm_16k.tobytes()
    
    def ai_to_telnyx(self, pcm_16k: bytes) -> bytes:
        """
        Convert AI services audio format to Telnyx format.
        
        AI: PCM 16-bit, 16kHz
        Telnyx: μ-law encoded, 8kHz
        
        Args:
            pcm_16k: PCM 16-bit 16kHz audio bytes
        
        Returns:
            μ-law encoded 8kHz audio bytes
        """
        # Convert bytes to numpy array
        pcm_array = np.frombuffer(pcm_16k, dtype=np.int16)
        
        # Resample 16kHz to 8kHz
        pcm_8k = self.resample(pcm_array, 16000, 8000)
        
        # Encode to μ-law
        ulaw_8k = self.pcm_to_ulaw(pcm_8k)
        
        return ulaw_8k
    
    def get_chunk_samples(self, sample_rate: int, duration_ms: int = 20) -> int:
        """
        Calculate number of samples for a given duration.
        
        Args:
            sample_rate: Sample rate in Hz
            duration_ms: Duration in milliseconds
        
        Returns:
            Number of samples
        """
        return int(sample_rate * duration_ms / 1000)


# Singleton instance
_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor() -> AudioProcessor:
    """
    Get the audio processor singleton instance.
    
    Returns:
        AudioProcessor instance
    """
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor
