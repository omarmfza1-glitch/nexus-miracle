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
from app.services.interruption_service import (
    InterruptionService,
    InterruptionState,
    get_interruption_service,
)
from app.services.llm_service import LLMService, get_llm_service
from app.services.text_correction_service import (
    TextCorrectionService,
    get_text_correction_service,
)
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
        interruption_service: InterruptionService | None = None,
        text_correction_service: TextCorrectionService | None = None,
    ) -> None:
        """
        Initialize the call service.
        
        Args:
            asr_service: ASR service instance (or use default)
            llm_service: LLM service instance (or use default)
            tts_service: TTS service instance (or use default)
            vad_service: VAD service instance (or use default)
            interruption_service: Interruption service instance (or use default)
            text_correction_service: Text correction service instance (or use default)
        """
        self._settings = get_settings()
        
        # Services
        self._asr = asr_service or get_asr_service()
        self._llm = llm_service or get_llm_service()
        self._tts = tts_service or get_tts_service()
        self._vad = vad_service or get_vad_service()
        self._interruption = interruption_service or get_interruption_service()
        self._text_correction = text_correction_service or get_text_correction_service()
        
        # Active sessions
        self._sessions: dict[str, ConversationSession] = {}
        
        # Audio buffer for accumulating speech
        self._audio_buffers: dict[str, bytes] = {}
        
        # Track if assistant is currently speaking (for interruption detection)
        self._is_assistant_speaking: dict[str, bool] = {}
        
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
        self._is_assistant_speaking[call_control_id] = False
        
        # Initialize interruption tracking
        self._interruption.create_session(call_control_id)
        
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
        Protected against multiple calls - will only generate greeting once.
        
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
        
        # Guard: Only generate greeting once
        if session.state in (CallState.ANSWERED, CallState.ACTIVE):
            if hasattr(session, '_greeting_audio') and session._greeting_audio:
                logger.debug(f"Returning cached greeting for: {call_control_id}")
                return session._greeting_audio
        
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
        
        # Cache greeting audio
        session._greeting_audio = audio
        
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
        
        With interruption handling:
        - When user interrupts, stop assistant and start accumulating
        - Continue accumulating until user is TRULY done (long silence)
        - Only say "تفضل" after brief silence, not after each segment
        - Process ALL accumulated speech as ONE request
        
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
        
        result: dict[str, Any] = {
            "vad": vad_result,
            "response_audio": None,
            "interruption": False,
            "clear_playback": False,
        }
        
        # Check if we're in interruption mode
        in_interruption_mode = self._interruption.is_in_interruption_mode(call_control_id)
        
        # Handle speech detection
        if vad_result["is_speaking"]:
            # Accumulate audio
            self._audio_buffers[call_control_id] += audio_bytes
            
            # Check if this is a NEW interruption (user speaks during assistant's turn)
            if self._is_assistant_speaking.get(call_control_id, False):
                if self._interruption.should_handle_interruption(call_control_id):
                    # Start new interruption - just clear playback, don't say anything yet
                    self._interruption.start_interruption(call_control_id)
                    result["interruption"] = True
                    result["clear_playback"] = True
                    logger.info(f"🛑 [{call_control_id}] Interruption - clearing playback, accumulating speech")
                    return result
            
            # If already in interruption mode, update timing
            if in_interruption_mode:
                self._interruption.on_speech_detected(call_control_id)
                return result
        
        # Check if speech ended
        if vad_result.get("speech_ended"):
            # If in interruption mode, use special handling
            if in_interruption_mode:
                int_result = self._interruption.on_speech_ended(call_control_id)
                
                if int_result["should_wait"]:
                    # Still waiting for more speech
                    logger.debug(f"[{call_control_id}] Speech segment ended, waiting for more...")
                    return result
            
            # Normal speech end processing (non-interruption or interruption complete)
            if self._audio_buffers[call_control_id]:
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
                    self._vad.reset()
        
        return result
    
    async def check_interruption_silence(self, call_control_id: str) -> dict[str, Any]:
        """
        Check if user has been silent long enough during interruption.
        
        Should be called periodically from the telephony router.
        
        Returns:
            dict with:
            - should_say_tafaddal: True if should play "تفضل"
            - should_process: True if should process accumulated speech
            - phrase_audio: Audio bytes for "تفضل" if applicable
            - response_audio: Full response audio if processing complete
        """
        result = {
            "should_say_tafaddal": False,
            "should_process": False,
            "phrase_audio": None,
            "response_audio": None,
        }
        
        # Check if we're in interruption mode
        if not self._interruption.is_in_interruption_mode(call_control_id):
            return result
        
        # Check silence duration
        check = self._interruption.check_silence_duration(call_control_id)
        
        if check["should_say_tafaddal"] and check["phrase"]:
            # Generate "تفضل" audio
            try:
                session = self._sessions.get(call_control_id)
                if session:
                    voice = Voice.SARA if session.active_voice == "sara" else Voice.NEXUS
                    audio = await self._tts.synthesize(
                        text=check["phrase"],
                        voice=voice,
                    )
                    result["should_say_tafaddal"] = True
                    result["phrase_audio"] = audio
                    logger.info(f"💬 [{call_control_id}] Generated: {check['phrase']}")
            except Exception as e:
                logger.error(f"Failed to generate tafaddal: {e}")
        
        elif check["should_process"]:
            # User is done - process all accumulated speech
            if self._audio_buffers[call_control_id]:
                try:
                    response_audio = await self._process_speech(
                        call_control_id,
                        self._audio_buffers[call_control_id],
                    )
                    result["should_process"] = True
                    result["response_audio"] = response_audio
                finally:
                    self._audio_buffers[call_control_id] = b""
                    self._vad.reset()
        
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
        transcription_result = await self._asr.transcribe(
            audio_bytes=audio_bytes,
            language="ar",  # TODO: Detect language
        )
        transcript = transcription_result.text.strip()
        
        logger.info(f"Transcription (raw): {transcript[:100] if len(transcript) > 100 else transcript}")
        
        # 2. Apply text correction
        original_transcript = transcript
        transcript = self._text_correction.correct(transcript)
        
        if transcript != original_transcript:
            logger.info(f"📝 Text corrected: '{original_transcript}' -> '{transcript}'")
        
        # Skip if transcription is empty (noise/silence detected by VAD)
        if not transcript:
            logger.debug("Empty transcription, skipping LLM response")
            return b""
        
        # Add user message
        session.add_message(
            role=ConversationRole.USER,
            content=transcript,
            audio_duration_ms=len(audio_bytes) // 32,  # 16kHz, 16-bit
        )
        
        # 2. Generate response
        conversation_history = session.get_conversation_for_llm()
        response_segments = await self._llm.generate_response(
            user_message=transcript,
            conversation_history=conversation_history,
            system_prompt=session.system_prompt,
        )
        
        # Extract text from segments
        response_text = " ".join([seg.text for seg in response_segments])
        
        logger.info(f"LLM response: {response_text[:100] if len(response_text) > 100 else response_text}")
        
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
        
        # Get interruption stats
        interruption_stats = self._interruption.end_session(call_control_id)
        summary["interruption_count"] = interruption_stats.get("interruption_count", 0)
        
        # Cleanup
        del self._sessions[call_control_id]
        if call_control_id in self._audio_buffers:
            del self._audio_buffers[call_control_id]
        if call_control_id in self._is_assistant_speaking:
            del self._is_assistant_speaking[call_control_id]
        
        logger.info(f"Session ended: {summary}")
        
        return summary
    
    async def handle_interruption(
        self,
        call_control_id: str,
    ) -> bytes:
        """
        Handle user interruption during assistant's speech.
        
        Generates "تفضل" audio to acknowledge the interruption.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            Audio bytes for the interruption phrase
        """
        session = self._sessions.get(call_control_id)
        if not session:
            logger.warning(f"No session for interruption: {call_control_id}")
            return b""
        
        # Get interruption phrase
        phrase = self._interruption.handle_interruption(call_control_id)
        
        # Clear audio buffer (user spoke, so their current speech is interrupted)
        self._audio_buffers[call_control_id] = b""
        
        # Synthesize the interruption phrase
        try:
            voice = Voice.SARA if session.active_voice == "sara" else Voice.NEXUS
            audio = await self._tts.synthesize(
                text=phrase,
                voice=voice,
            )
            
            # Mark that we're now waiting for user
            self._interruption.mark_waiting_for_user(call_control_id)
            
            logger.info(f"🛑 Interruption phrase generated: {phrase} ({len(audio)} bytes)")
            
            return audio
            
        except Exception as e:
            logger.error(f"Failed to generate interruption phrase: {e}")
            return b""
    
    def set_assistant_speaking(self, call_control_id: str, is_speaking: bool) -> None:
        """
        Set whether the assistant is currently speaking.
        
        Args:
            call_control_id: Telnyx call control ID
            is_speaking: True if assistant is speaking
        """
        self._is_assistant_speaking[call_control_id] = is_speaking
        
        if is_speaking:
            self._interruption.set_assistant_speaking(call_control_id)
        else:
            self._interruption.set_idle(call_control_id)
        
        logger.debug(f"Assistant speaking: {is_speaking} for {call_control_id}")
    
    def is_assistant_speaking(self, call_control_id: str) -> bool:
        """
        Check if assistant is currently speaking.
        
        Args:
            call_control_id: Telnyx call control ID
            
        Returns:
            True if assistant is speaking
        """
        return self._is_assistant_speaking.get(call_control_id, False)
    
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
