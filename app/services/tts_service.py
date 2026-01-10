"""
Nexus Miracle - TTS Service

ElevenLabs Flash v2.5 integration for text-to-speech synthesis.
Supports dual voices (Sara and Nexus) for the medical assistant.
Target: <100ms TTFB (Time to First Byte).
"""

import asyncio
import time
from enum import Enum
from typing import Any, AsyncGenerator

from loguru import logger

from app.config import get_settings
from app.exceptions import SynthesisError, TTSException, VoiceNotFoundError


class Voice(str, Enum):
    """Available voices for the assistant."""
    
    SARA = "sara"
    NEXUS = "nexus"


class TTSService:
    """
    Text-to-Speech service using ElevenLabs Flash v2.5.
    
    Optimized for low-latency voice synthesis with dual
    voice support for the Nexus Miracle assistant.
    
    Voices:
    - Sara: Female Arabic voice (receptionist persona)
    - Nexus: Male Arabic voice (medical assistant persona)
    
    Target: <100ms Time to First Byte.
    """
    
    # Voice configurations
    VOICE_CONFIGS = {
        Voice.SARA: {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.4,
            "speed": 1.0,
        },
        Voice.NEXUS: {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.2,
            "speed": 0.95,
        },
    }
    
    def __init__(self) -> None:
        """Initialize the TTS service."""
        self._settings = get_settings()
        self._client: Any = None
        self._is_initialized = False
        self._active_voice = Voice.SARA
        
        # Voice ID cache
        self._voice_ids: dict[Voice, str] = {}
        
        # Statistics
        self._total_syntheses = 0
        self._total_ttfb_ms = 0.0
        self._total_bytes = 0
        
        logger.info("TTSService created")
    
    async def initialize(self) -> None:
        """
        Initialize the ElevenLabs client for TTS.
        
        Raises:
            TTSException: If initialization fails
        """
        if self._is_initialized:
            return
        
        try:
            from elevenlabs import ElevenLabs
            
            api_key = self._settings.elevenlabs_api_key
            if not api_key:
                raise TTSException(
                    message="ElevenLabs API key not configured",
                    details={"setting": "elevenlabs_api_key"},
                )
            
            self._client = ElevenLabs(api_key=api_key)
            
            # Get voice IDs from settings
            sara_id = self._settings.elevenlabs_voice_sara
            nexus_id = self._settings.elevenlabs_voice_nexus
            
            if sara_id:
                self._voice_ids[Voice.SARA] = sara_id
            if nexus_id:
                self._voice_ids[Voice.NEXUS] = nexus_id
            
            self._is_initialized = True
            logger.info(
                f"TTSService initialized with voices: "
                f"Sara={sara_id[:8] if sara_id else 'N/A'}..., "
                f"Nexus={nexus_id[:8] if nexus_id else 'N/A'}..."
            )
            
        except ImportError:
            logger.warning("elevenlabs package not installed")
            self._is_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise TTSException(
                message="Failed to initialize TTS service",
                details={"error": str(e)},
            )
    
    def _get_voice_id(self, voice: Voice) -> str:
        """Get ElevenLabs voice ID for a voice."""
        if voice not in self._voice_ids:
            raise VoiceNotFoundError(
                message=f"Voice '{voice.value}' not configured",
                details={"voice": voice.value},
            )
        return self._voice_ids[voice]
    
    async def synthesize(
        self,
        text: str,
        voice: Voice | str = Voice.SARA,
        output_format: str = "pcm_16000",
    ) -> bytes:
        """
        Synthesize text to audio.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (SARA or NEXUS)
            output_format: Audio output format
        
        Returns:
            Audio bytes (PCM 16-bit 16kHz)
        
        Raises:
            SynthesisError: If synthesis fails
            VoiceNotFoundError: If voice is not available
        """
        if not self._is_initialized:
            await self.initialize()
        
        # Handle string voice names
        if isinstance(voice, str):
            voice = Voice(voice.lower())
        
        if not self._client:
            logger.warning("TTS client not available")
            return b""
        
        start_time = time.time()
        
        try:
            voice_id = self._get_voice_id(voice)
            voice_config = self.VOICE_CONFIGS[voice]
            
            logger.debug(f"Synthesizing {len(text)} chars as {voice.value}")
            
            # Call ElevenLabs TTS API
            audio = await asyncio.to_thread(
                self._client.text_to_speech.convert,
                text=text,
                voice_id=voice_id,
                model_id="eleven_flash_v2_5",
                output_format=output_format,
                voice_settings={
                    "stability": voice_config["stability"],
                    "similarity_boost": voice_config["similarity_boost"],
                    "style": voice_config.get("style", 0.0),
                    "use_speaker_boost": True,
                },
            )
            
            # Collect all audio bytes
            audio_bytes = b"".join(audio) if hasattr(audio, '__iter__') else audio
            
            # Log metrics
            latency_ms = (time.time() - start_time) * 1000
            self._total_syntheses += 1
            self._total_bytes += len(audio_bytes)
            
            logger.info(f"TTS ({latency_ms:.0f}ms): {voice.value}, {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except VoiceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise SynthesisError(
                message="Text-to-speech synthesis failed",
                details={"error": str(e), "text_length": len(text)},
            )
    
    async def synthesize_stream(
        self,
        text: str,
        voice: Voice | str = Voice.SARA,
        output_format: str = "pcm_16000",
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio for lower latency.
        
        Yields audio chunks as they are generated.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            output_format: Audio format
        
        Yields:
            Audio byte chunks
        """
        if not self._is_initialized:
            await self.initialize()
        
        if isinstance(voice, str):
            voice = Voice(voice.lower())
        
        if not self._client:
            return
        
        start_time = time.time()
        first_chunk_time = None
        total_bytes = 0
        
        try:
            voice_id = self._get_voice_id(voice)
            voice_config = self.VOICE_CONFIGS[voice]
            
            # Stream from ElevenLabs (convert returns an iterator when streaming)
            audio_stream = self._client.text_to_speech.stream(
                text=text,
                voice_id=voice_id,
                model_id="eleven_flash_v2_5",
                output_format=output_format,
                voice_settings={
                    "stability": voice_config["stability"],
                    "similarity_boost": voice_config["similarity_boost"],
                    "style": voice_config.get("style", 0.0),
                },
            )
            
            for chunk in audio_stream:
                if first_chunk_time is None:
                    first_chunk_time = time.time()
                    ttfb_ms = (first_chunk_time - start_time) * 1000
                    self._total_ttfb_ms += ttfb_ms
                    logger.debug(f"TTS TTFB: {ttfb_ms:.0f}ms")
                
                total_bytes += len(chunk)
                yield chunk
            
            self._total_syntheses += 1
            self._total_bytes += total_bytes
            
        except Exception as e:
            logger.error(f"TTS streaming failed: {e}")
            raise SynthesisError(
                message="TTS streaming failed",
                details={"error": str(e)},
            )
    
    async def synthesize_with_input_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        voice: Voice = Voice.SARA,
        output_format: str = "pcm_16000",
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesis with streaming text input.
        
        Lowest latency by starting synthesis before full text available.
        """
        if not self._is_initialized:
            await self.initialize()
        
        if not self._client:
            return
        
        try:
            voice_id = self._get_voice_id(voice)
            voice_config = self.VOICE_CONFIGS[voice]
            
            # Collect text from stream
            text_buffer = ""
            async for text_chunk in text_stream:
                text_buffer += text_chunk
            
            # Synthesize complete text
            # Note: True input streaming requires ElevenLabs websocket API
            async for audio_chunk in self.synthesize_stream(
                text_buffer,
                voice,
                output_format,
            ):
                yield audio_chunk
                
        except Exception as e:
            logger.error(f"Input stream synthesis failed: {e}")
            raise
    
    def switch_voice(self, new_voice: Voice) -> None:
        """Switch the active voice."""
        if new_voice not in Voice:
            raise VoiceNotFoundError(
                message=f"Unknown voice: {new_voice}",
                details={"voice": str(new_voice)},
            )
        
        old_voice = self._active_voice
        self._active_voice = new_voice
        logger.debug(f"Voice switched: {old_voice.value} -> {new_voice.value}")
    
    def get_stats(self) -> dict[str, float]:
        """Get TTS performance statistics."""
        avg_ttfb = 0.0
        if self._total_syntheses > 0:
            avg_ttfb = self._total_ttfb_ms / self._total_syntheses
        
        return {
            "total_syntheses": self._total_syntheses,
            "average_ttfb_ms": avg_ttfb,
            "total_bytes": self._total_bytes,
        }
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._client = None
        logger.info("TTSService shutdown")


# Singleton instance
_tts_service: TTSService | None = None


def get_tts_service() -> TTSService:
    """Get the TTS service singleton instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
