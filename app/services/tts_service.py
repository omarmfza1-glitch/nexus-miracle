"""
Nexus Miracle - TTS Service

ElevenLabs Flash v2.5 integration for text-to-speech synthesis.
Supports dual voices (Sara and Nexus) for the medical assistant.
"""

from enum import Enum
from typing import Any, AsyncGenerator

from loguru import logger

from app.config import get_settings
from app.exceptions import SynthesisError, TTSException, VoiceNotFoundError


class Voice(str, Enum):
    """Available voices for the assistant."""
    
    SARA = "sara"  # Primary Arabic female voice
    NEXUS = "nexus"  # Secondary Arabic male voice


class TTSService:
    """
    Text-to-Speech service using ElevenLabs Flash v2.5.
    
    Optimized for low-latency voice synthesis with dual
    voice support for the Nexus Miracle assistant.
    """
    
    def __init__(self) -> None:
        """Initialize the TTS service."""
        self._settings = get_settings()
        self._client: Any = None
        self._is_initialized = False
        self._voices: dict[Voice, str] = {}
        
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
            # TODO: Initialize ElevenLabs client
            # from elevenlabs import ElevenLabs
            # self._client = ElevenLabs(api_key=self._settings.elevenlabs_api_key)
            
            # Map voice enum to voice IDs
            self._voices = {
                Voice.SARA: self._settings.elevenlabs_voice_sara,
                Voice.NEXUS: self._settings.elevenlabs_voice_nexus,
            }
            
            self._is_initialized = True
            logger.info("TTSService initialized with dual voice support")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise TTSException(
                message="Failed to initialize TTS service",
                details={"error": str(e)},
            )
    
    def _get_voice_id(self, voice: Voice) -> str:
        """
        Get the ElevenLabs voice ID for a voice.
        
        Args:
            voice: Voice enum value
        
        Returns:
            Voice ID string
        
        Raises:
            VoiceNotFoundError: If voice is not configured
        """
        voice_id = self._voices.get(voice)
        
        if not voice_id:
            raise VoiceNotFoundError(
                message=f"Voice not configured: {voice.value}",
                details={"voice": voice.value},
            )
        
        return voice_id
    
    async def synthesize(
        self,
        text: str,
        voice: Voice = Voice.SARA,
        output_format: str = "pcm_16000",
    ) -> bytes:
        """
        Synthesize text to audio.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (SARA or NEXUS)
            output_format: Audio output format
        
        Returns:
            Audio bytes
        
        Raises:
            SynthesisError: If synthesis fails
            VoiceNotFoundError: If voice is not available
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            voice_id = self._get_voice_id(voice)
            
            logger.debug(
                f"Synthesizing {len(text)} chars with voice={voice.value}"
            )
            
            # TODO: Implement actual synthesis
            # audio = await self._client.text_to_speech.convert(
            #     text=text,
            #     voice_id=voice_id,
            #     model_id=self._settings.elevenlabs_model,
            #     output_format=output_format,
            #     voice_settings={
            #         "stability": self._settings.elevenlabs_stability,
            #         "similarity_boost": self._settings.elevenlabs_similarity_boost,
            #     },
            # )
            # return audio
            
            # Placeholder - return empty audio bytes
            return b"\x00" * 1600  # 100ms of silence at 16kHz
            
        except VoiceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            raise SynthesisError(
                message="Failed to synthesize speech",
                details={"error": str(e), "text_length": len(text)},
            )
    
    async def synthesize_stream(
        self,
        text: str,
        voice: Voice = Voice.SARA,
        output_format: str = "pcm_16000",
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized audio for lower latency.
        
        Yields audio chunks as they are generated, enabling
        immediate playback while synthesis continues.
        
        Args:
            text: Text to synthesize
            voice: Voice to use
            output_format: Audio output format
        
        Yields:
            Audio byte chunks
        
        Raises:
            SynthesisError: If synthesis fails
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            voice_id = self._get_voice_id(voice)
            
            logger.debug(
                f"Starting streaming synthesis: {len(text)} chars, voice={voice.value}"
            )
            
            # TODO: Implement streaming synthesis
            # async for chunk in self._client.text_to_speech.convert_as_stream(
            #     text=text,
            #     voice_id=voice_id,
            #     model_id=self._settings.elevenlabs_model,
            #     output_format=output_format,
            # ):
            #     yield chunk
            
            # Placeholder
            yield b"\x00" * 1600
            yield b"\x00" * 1600
            
        except VoiceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Streaming synthesis failed: {e}")
            raise SynthesisError(
                message="Streaming synthesis failed",
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
        
        Enables the lowest latency by starting synthesis
        before the full text is available.
        
        Args:
            text_stream: Async generator yielding text chunks
            voice: Voice to use
            output_format: Audio output format
        
        Yields:
            Audio byte chunks
        
        Raises:
            SynthesisError: If synthesis fails
        """
        if not self._is_initialized:
            await self.initialize()
        
        try:
            voice_id = self._get_voice_id(voice)
            
            logger.debug(f"Starting input-streaming synthesis, voice={voice.value}")
            
            # TODO: Implement input streaming synthesis
            # This would use ElevenLabs websocket API for
            # true streaming input-to-output synthesis
            
            # Placeholder
            async for text_chunk in text_stream:
                yield b"\x00" * len(text_chunk) * 100
                
        except Exception as e:
            logger.error(f"Input-streaming synthesis failed: {e}")
            raise SynthesisError(
                message="Input-streaming synthesis failed",
                details={"error": str(e)},
            )
    
    async def switch_voice(self, new_voice: Voice) -> None:
        """
        Switch the active voice.
        
        Used for seamless voice transitions during a call.
        
        Args:
            new_voice: New voice to use
        
        Raises:
            VoiceNotFoundError: If voice is not available
        """
        # Validate voice exists
        self._get_voice_id(new_voice)
        logger.info(f"Voice switched to: {new_voice.value}")
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        self._is_initialized = False
        self._client = None
        self._voices = {}
        logger.info("TTSService shutdown")


# Singleton instance
_tts_service: TTSService | None = None


def get_tts_service() -> TTSService:
    """
    Get the TTS service singleton instance.
    
    Returns:
        TTSService instance
    """
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
