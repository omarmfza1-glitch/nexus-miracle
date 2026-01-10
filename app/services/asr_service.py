"""
Nexus Miracle - ASR Service

ElevenLabs Scribe integration for speech-to-text transcription.
Designed for real-time streaming audio input.
Target: <300ms transcription latency.
"""

import asyncio
import io
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from loguru import logger

from app.config import get_settings
from app.exceptions import ASRException, TranscriptionError


@dataclass
class TranscriptionResult:
    """Result of speech transcription."""
    
    text: str
    confidence: float = 1.0
    language: str = "ar"
    duration_ms: float = 0.0
    is_final: bool = True


class ASRService:
    """
    Automatic Speech Recognition service using ElevenLabs Scribe.
    
    Handles real-time audio transcription with streaming support
    for low-latency voice applications.
    
    Target latency: <300ms for complete transcription.
    """
    
    def __init__(self) -> None:
        """Initialize the ASR service."""
        self._settings = get_settings()
        self._client: Any = None
        self._is_initialized = False
        
        # Statistics
        self._total_transcriptions = 0
        self._total_latency_ms = 0.0
        
        logger.info("ASRService created")
    
    async def initialize(self) -> None:
        """
        Initialize the ElevenLabs client for ASR.
        
        Raises:
            ASRException: If initialization fails
        """
        if self._is_initialized:
            return
        
        try:
            from elevenlabs import ElevenLabs
            
            api_key = self._settings.elevenlabs_api_key
            if not api_key:
                raise ASRException(
                    message="ElevenLabs API key not configured",
                    details={"setting": "elevenlabs_api_key"},
                )
            
            self._client = ElevenLabs(api_key=api_key)
            self._is_initialized = True
            logger.info("ASRService initialized with ElevenLabs Scribe")
            
        except ImportError:
            logger.warning("elevenlabs package not installed, ASR will be unavailable")
            self._is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize ASR service: {e}")
            raise ASRException(
                message="Failed to initialize ASR service",
                details={"error": str(e)},
            )
    
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "ar",
    ) -> TranscriptionResult:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM, 16kHz)
            language: Language code (ar for Arabic, en for English)
        
        Returns:
            TranscriptionResult with text and metadata
        
        Raises:
            TranscriptionError: If transcription fails
        """
        if not self._is_initialized:
            await self.initialize()
        
        if not self._client:
            logger.warning("ASR client not available, returning placeholder")
            return TranscriptionResult(
                text="[ASR unavailable]",
                confidence=0.0,
                language=language,
            )
        
        start_time = time.time()
        
        try:
            logger.debug(f"Transcribing {len(audio_bytes)} bytes, language={language}")
            
            # Convert PCM to WAV format for API
            wav_audio = self._pcm_to_wav(audio_bytes)
            
            # Create a file-like object for the API
            audio_file = io.BytesIO(wav_audio)
            audio_file.name = "audio.wav"
            
            # Call ElevenLabs Speech-to-Text API
            result = await asyncio.to_thread(
                self._client.speech_to_text.convert,
                file=audio_file,
                model_id="scribe_v2",
                language_code=language,
            )
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            self._total_transcriptions += 1
            self._total_latency_ms += latency_ms
            
            transcription = TranscriptionResult(
                text=result.text,
                confidence=getattr(result, 'confidence', 1.0),
                language=getattr(result, 'detected_language', language),
                duration_ms=latency_ms,
                is_final=True,
            )
            
            logger.info(f"ASR ({latency_ms:.0f}ms): {transcription.text}")
            return transcription
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(
                message="Speech transcription failed",
                details={"error": str(e), "audio_length": len(audio_bytes)},
            )
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "ar",
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        Stream transcription for real-time audio.
        
        Accumulates audio chunks and transcribes when silence detected.
        
        Args:
            audio_stream: Async generator yielding audio chunks
            language: Language code
        
        Yields:
            TranscriptionResult for each detected utterance
        """
        if not self._is_initialized:
            await self.initialize()
        
        audio_buffer: list[bytes] = []
        buffer_size = 0
        min_buffer_ms = 500  # Minimum audio to transcribe
        samples_per_ms = 16  # 16kHz sample rate
        
        try:
            async for chunk in audio_stream:
                audio_buffer.append(chunk)
                buffer_size += len(chunk)
                
                # Calculate buffer duration
                buffer_samples = buffer_size // 2  # 16-bit = 2 bytes
                buffer_ms = buffer_samples / samples_per_ms
                
                # Transcribe when buffer has enough audio
                if buffer_ms >= min_buffer_ms:
                    # Combine buffer
                    combined = b"".join(audio_buffer)
                    audio_buffer.clear()
                    buffer_size = 0
                    
                    # Transcribe
                    result = await self.transcribe(combined, language)
                    if result.text.strip():
                        yield result
            
            # Transcribe remaining audio
            if audio_buffer:
                combined = b"".join(audio_buffer)
                result = await self.transcribe(combined, language)
                if result.text.strip():
                    yield result
                    
        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")
            raise TranscriptionError(
                message="Streaming transcription failed",
                details={"error": str(e)},
            )
    
    def _pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 16000) -> bytes:
        """
        Convert raw PCM data to WAV format.
        
        Args:
            pcm_data: Raw 16-bit PCM audio
            sample_rate: Sample rate in Hz
        
        Returns:
            WAV formatted audio bytes
        """
        import struct
        
        # WAV header
        channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)
        
        # Build WAV header
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + data_size,
            b'WAVE',
            b'fmt ',
            16,  # Subchunk1Size
            1,   # AudioFormat (PCM)
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits_per_sample,
            b'data',
            data_size,
        )
        
        return wav_header + pcm_data
    
    def get_stats(self) -> dict[str, float]:
        """Get ASR performance statistics."""
        avg_latency = 0.0
        if self._total_transcriptions > 0:
            avg_latency = self._total_latency_ms / self._total_transcriptions
        
        return {
            "total_transcriptions": self._total_transcriptions,
            "average_latency_ms": avg_latency,
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._client = None
        logger.info("ASRService shutdown")


# Singleton instance
_asr_service: ASRService | None = None


def get_asr_service() -> ASRService:
    """Get the ASR service singleton instance."""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
