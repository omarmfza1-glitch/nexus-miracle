"""
Nexus Miracle - Call Service

Orchestration service that coordinates all AI services
for handling phone calls end-to-end.
"""

from typing import Any
from uuid import UUID

from loguru import logger

from app.config import get_settings
from app.exceptions import NexusMiracleException
from app.models.conversation import (
    CallState,
    ConversationMessage,
    ConversationRole,
    ConversationSession,
)
from app.services.asr_service import ASRService, get_asr_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.tts_service import TTSService, Voice, get_tts_service
from app.services.vad_service import VADService, get_vad_service


class CallService:
    """
    Call orchestration service.
    
    Coordinates the flow of:
    1. Audio input -> VAD -> ASR -> Transcript
    2. Transcript -> LLM -> Response text
    3. Response text -> TTS -> Audio output
    
    Manages call sessions and conversation state.
    """
    
    def __init__(
        self,
        asr_service: ASRService | None = None,
        llm_service: LLMService | None = None,
        tts_service: TTSService | None = None,
        vad_service: VADService | None = None,
    ) -> None:
        """
        Initialize the call service.
        
        Args:
            asr_service: ASR service instance (or use default)
            llm_service: LLM service instance (or use default)
            tts_service: TTS service instance (or use default)
            vad_service: VAD service instance (or use default)
        """
        self._settings = get_settings()
        
        # Services
        self._asr = asr_service or get_asr_service()
        self._llm = llm_service or get_llm_service()
        self._tts = tts_service or get_tts_service()
        self._vad = vad_service or get_vad_service()
        
        # Active sessions
        self._sessions: dict[str, ConversationSession] = {}
        
        # Audio buffer for accumulating speech
        self._audio_buffers: dict[str, bytes] = {}
        
        logger.info("CallService created")
    
    async def initialize(self) -> None:
        """Initialize all services."""
        logger.info("Initializing CallService and dependencies...")
        
        await self._asr.initialize()
        await self._llm.initialize()
        await self._tts.initialize()
        await self._vad.initialize()
        
        logger.info("CallService fully initialized")
    
    async def create_session(
        self,
        call_control_id: str,
        caller_phone: str,
        called_phone: str,
    ) -> ConversationSession:
        """
        Create a new call session.
        
        Args:
            call_control_id: Telnyx call control ID
            caller_phone: Caller's phone number
            called_phone: Called phone number
        
        Returns:
            New conversation session
        """
        session = ConversationSession(
            call_control_id=call_control_id,
            caller_phone=caller_phone,
            called_phone=called_phone,
            system_prompt=self._llm.DEFAULT_SYSTEM_PROMPT,
        )
        
        self._sessions[call_control_id] = session
        self._audio_buffers[call_control_id] = b""
        
        logger.info(
            f"Created session {session.id} for call {call_control_id}"
        )
        
        return session
    
    def get_session(self, call_control_id: str) -> ConversationSession | None:
        """
        Get an existing session by call control ID.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            Session if found, None otherwise
        """
        return self._sessions.get(call_control_id)
    
    async def handle_call_answered(
        self,
        call_control_id: str,
    ) -> bytes:
        """
        Handle call answered event.
        
        Updates session state and generates greeting.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            Greeting audio bytes
        """
        session = self._sessions.get(call_control_id)
        if not session:
            raise NexusMiracleException(
                message="Session not found",
                details={"call_control_id": call_control_id},
            )
        
        session.update_state(CallState.ANSWERED)
        
        # Generate greeting
        greeting = "مرحباً بك في نيكسوس ميراكل. كيف يمكنني مساعدتك اليوم؟"
        
        # Add to conversation
        session.add_message(
            role=ConversationRole.ASSISTANT,
            content=greeting,
        )
        
        # Synthesize greeting
        audio = await self._tts.synthesize(
            text=greeting,
            voice=Voice.SARA,
        )
        
        session.update_state(CallState.ACTIVE)
        
        logger.info(f"Call answered, greeting sent: {call_control_id}")
        
        return audio
    
    async def process_audio_chunk(
        self,
        call_control_id: str,
        audio_bytes: bytes,
    ) -> dict[str, Any]:
        """
        Process incoming audio chunk.
        
        Runs VAD to detect speech, accumulates audio,
        and triggers processing when speech ends.
        
        Args:
            call_control_id: Telnyx call control ID
            audio_bytes: Raw audio bytes
        
        Returns:
            Processing result with state and optional response audio
        """
        session = self._sessions.get(call_control_id)
        if not session:
            return {"error": "Session not found"}
        
        # Run VAD
        vad_result = await self._vad.process_audio(audio_bytes)
        
        # Accumulate audio if speech detected
        if vad_result["is_speaking"]:
            self._audio_buffers[call_control_id] += audio_bytes
        
        result: dict[str, Any] = {
            "vad": vad_result,
            "response_audio": None,
        }
        
        # Check if speech ended - trigger response generation
        if vad_result.get("speech_ended") and self._audio_buffers[call_control_id]:
            logger.debug(f"Speech ended, processing: {call_control_id}")
            
            try:
                # Process accumulated audio
                response_audio = await self._process_speech(
                    call_control_id,
                    self._audio_buffers[call_control_id],
                )
                
                result["response_audio"] = response_audio
                
            finally:
                # Clear buffer
                self._audio_buffers[call_control_id] = b""
                self._vad.reset_state()
        
        return result
    
    async def _process_speech(
        self,
        call_control_id: str,
        audio_bytes: bytes,
    ) -> bytes:
        """
        Process complete speech segment.
        
        Full pipeline: ASR -> LLM -> TTS
        
        Args:
            call_control_id: Call control ID
            audio_bytes: Complete speech audio
        
        Returns:
            Response audio bytes
        """
        session = self._sessions[call_control_id]
        
        # 1. Transcribe speech
        transcript = await self._asr.transcribe_audio(
            audio_bytes=audio_bytes,
            language="ar",  # TODO: Detect language
        )
        
        logger.info(f"Transcription: {transcript[:100]}...")
        
        # Add user message
        session.add_message(
            role=ConversationRole.USER,
            content=transcript,
            audio_duration_ms=len(audio_bytes) // 32,  # 16kHz, 16-bit
        )
        
        # 2. Generate response
        messages = session.get_conversation_for_llm()
        response_text = await self._llm.generate_response(
            messages=messages,
            system_prompt=session.system_prompt,
        )
        
        logger.info(f"LLM response: {response_text[:100]}...")
        
        # Add assistant message
        session.add_message(
            role=ConversationRole.ASSISTANT,
            content=response_text,
        )
        
        # 3. Synthesize response
        voice = Voice.SARA if session.active_voice == "sara" else Voice.NEXUS
        response_audio = await self._tts.synthesize(
            text=response_text,
            voice=voice,
        )
        
        return response_audio
    
    async def end_session(
        self,
        call_control_id: str,
    ) -> dict[str, Any]:
        """
        End a call session.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            Session summary
        """
        session = self._sessions.get(call_control_id)
        if not session:
            return {"error": "Session not found"}
        
        session.update_state(CallState.ENDED)
        
        summary = {
            "session_id": str(session.id),
            "duration_seconds": session.duration_seconds,
            "message_count": session.message_count,
            "final_state": session.state.value,
        }
        
        # Cleanup
        del self._sessions[call_control_id]
        if call_control_id in self._audio_buffers:
            del self._audio_buffers[call_control_id]
        
        logger.info(f"Session ended: {summary}")
        
        return summary
    
    async def switch_voice(
        self,
        call_control_id: str,
        voice: str,
    ) -> None:
        """
        Switch the active voice for a session.
        
        Args:
            call_control_id: Call control ID
            voice: Voice name ("sara" or "nexus")
        """
        session = self._sessions.get(call_control_id)
        if session:
            session.active_voice = voice
            logger.info(f"Voice switched to {voice}: {call_control_id}")
    
    def get_active_call_count(self) -> int:
        """Get count of active calls."""
        return len(self._sessions)
    
    async def shutdown(self) -> None:
        """Cleanup all resources."""
        logger.info("Shutting down CallService...")
        
        # End all sessions
        for call_id in list(self._sessions.keys()):
            await self.end_session(call_id)
        
        # Shutdown services
        await self._asr.shutdown()
        await self._llm.shutdown()
        await self._tts.shutdown()
        await self._vad.shutdown()
        
        logger.info("CallService shutdown complete")


# Singleton instance
_call_service: CallService | None = None


def get_call_service() -> CallService:
    """
    Get the call service singleton instance.
    
    Returns:
        CallService instance
    """
    global _call_service
    if _call_service is None:
        _call_service = CallService()
    return _call_service
