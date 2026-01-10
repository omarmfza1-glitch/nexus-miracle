"""
Nexus Miracle - Pipeline Service

Main orchestrator for the AI processing pipeline.
Coordinates VAD → ASR → LLM → TTS with filler management.
Target: <800ms total latency.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from loguru import logger

from app.config import get_settings
from app.services.asr_service import ASRService, get_asr_service, TranscriptionResult
from app.services.audio_sequencer import AudioSequencer, SegmentPriority
from app.services.filler_service import FillerService, get_filler_service
from app.services.llm_service import LLMService, get_llm_service, ResponseSegment, ConversationContext
from app.services.tts_service import TTSService, get_tts_service, Voice
from app.services.vad_service import VADService, get_vad_service, VADEvent


@dataclass
class CallSession:
    """Active call session state."""
    
    call_control_id: str
    caller_phone: str = ""
    called_phone: str = ""
    
    # Conversation state
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    system_prompt: str = ""
    
    # Audio management
    audio_sequencer: AudioSequencer = field(default_factory=AudioSequencer)
    audio_buffer: bytes = b""
    
    # Flags
    is_speaking: bool = False
    is_processing: bool = False
    greeting_sent: bool = False
    
    # Metrics
    total_turns: int = 0
    total_latency_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
        })
    
    def get_average_latency(self) -> float:
        """Get average turn latency."""
        if self.total_turns == 0:
            return 0.0
        return self.total_latency_ms / self.total_turns


class PipelineService:
    """
    AI Processing Pipeline Orchestrator.
    
    Coordinates the full voice AI pipeline:
    1. VAD detects speech boundaries
    2. ASR transcribes speech to text
    3. LLM generates response
    4. TTS synthesizes speech
    5. Audio sequencer manages playback
    
    Features:
    - Filler phrases mask processing latency
    - Barge-in support for interruptions
    - Dual persona (Sara/Nexus) voice switching
    - Database context integration
    
    Target: <800ms total pipeline latency.
    """
    
    # Filler delay threshold in milliseconds
    FILLER_DELAY_MS = 800
    
    def __init__(
        self,
        vad: VADService | None = None,
        asr: ASRService | None = None,
        llm: LLMService | None = None,
        tts: TTSService | None = None,
        filler: FillerService | None = None,
    ) -> None:
        """
        Initialize the pipeline service.
        
        Args:
            vad: VAD service (or use singleton)
            asr: ASR service (or use singleton)
            llm: LLM service (or use singleton)
            tts: TTS service (or use singleton)
            filler: Filler service (or use singleton)
        """
        self._settings = get_settings()
        
        # Services
        self._vad = vad or get_vad_service()
        self._asr = asr or get_asr_service()
        self._llm = llm or get_llm_service()
        self._tts = tts or get_tts_service()
        self._filler = filler or get_filler_service()
        
        # Active sessions
        self._sessions: dict[str, CallSession] = {}
        
        # Statistics
        self._total_turns_processed = 0
        self._total_pipeline_ms = 0.0
        
        self._is_initialized = False
        logger.info("PipelineService created")
    
    async def initialize(self) -> None:
        """Initialize all services."""
        if self._is_initialized:
            return
        
        await asyncio.gather(
            self._vad.initialize(),
            self._asr.initialize(),
            self._llm.initialize(),
            self._tts.initialize(),
            self._filler.initialize(),
        )
        
        self._is_initialized = True
        logger.info("PipelineService initialized")
    
    def create_session(
        self,
        call_control_id: str,
        caller_phone: str = "",
        called_phone: str = "",
        system_prompt: str | None = None,
    ) -> CallSession:
        """
        Create a new call session.
        
        Args:
            call_control_id: Unique call identifier
            caller_phone: Caller's phone number
            called_phone: Called phone number
            system_prompt: Custom system prompt
        
        Returns:
            New CallSession instance
        """
        session = CallSession(
            call_control_id=call_control_id,
            caller_phone=caller_phone,
            called_phone=called_phone,
            system_prompt=system_prompt or self._llm.DEFAULT_SYSTEM_PROMPT,
        )
        
        self._sessions[call_control_id] = session
        logger.info(f"Session created: {call_control_id}")
        
        return session
    
    def get_session(self, call_control_id: str) -> CallSession | None:
        """Get an existing session."""
        return self._sessions.get(call_control_id)
    
    async def process_turn(
        self,
        session: CallSession,
        audio_buffer: bytes,
        output_callback: Callable[[bytes], Awaitable[None]],
        db_context: ConversationContext | None = None,
    ) -> dict[str, Any]:
        """
        Process a complete conversation turn.
        
        Full pipeline: ASR → Filler → LLM → TTS → Playback
        
        Args:
            session: Call session
            audio_buffer: Accumulated speech audio
            output_callback: Function to send audio chunks
            db_context: Database context for LLM
        
        Returns:
            Turn processing results with latency metrics
        """
        if not self._is_initialized:
            await self.initialize()
        
        start_time = time.time()
        metrics = {
            "asr_ms": 0.0,
            "llm_ms": 0.0,
            "tts_ms": 0.0,
            "total_ms": 0.0,
            "segments": 0,
            "filler_used": False,
        }
        
        session.is_processing = True
        
        try:
            # 1. Transcribe audio
            asr_start = time.time()
            transcript = await self._asr.transcribe(audio_buffer)
            metrics["asr_ms"] = (time.time() - asr_start) * 1000
            
            logger.info(f"ASR ({metrics['asr_ms']:.0f}ms): {transcript.text}")
            
            if not transcript.text.strip():
                return metrics
            
            # 2. Add to conversation history
            session.add_message("user", transcript.text)
            
            # 3. Check for empathy filler
            empathy_filler = self._filler.get_empathy_filler(transcript.text)
            if empathy_filler:
                phrase, audio = empathy_filler
                if audio:
                    await session.audio_sequencer.add_segment(
                        audio,
                        speaker="sara",
                        priority=SegmentPriority.HIGH,
                        text=phrase.text,
                    )
                    metrics["filler_used"] = True
            
            # 4. Start delayed filler task
            filler_task = asyncio.create_task(
                self._delayed_filler(session, delay_ms=self.FILLER_DELAY_MS)
            )
            
            # 5. Generate LLM response
            llm_start = time.time()
            response_segments = await self._llm.generate_response(
                user_message=transcript.text,
                conversation_history=session.conversation_history,
                system_prompt=session.system_prompt,
                db_context=db_context,
            )
            metrics["llm_ms"] = (time.time() - llm_start) * 1000
            metrics["segments"] = len(response_segments)
            
            logger.info(f"LLM ({metrics['llm_ms']:.0f}ms): {len(response_segments)} segments")
            
            # 6. Cancel filler if response arrived quickly
            filler_task.cancel()
            try:
                await filler_task
            except asyncio.CancelledError:
                pass
            
            # 7. Synthesize and queue each segment
            tts_start = time.time()
            for segment in response_segments:
                # Synthesize audio
                voice = Voice(segment.speaker)
                audio = await self._tts.synthesize(segment.text, voice)
                
                # Queue for playback
                await session.audio_sequencer.add_segment(
                    audio,
                    speaker=segment.speaker,
                    priority=SegmentPriority.NORMAL,
                    text=segment.text,
                )
                
                # Add to history
                session.add_message(segment.speaker, segment.text)
            
            metrics["tts_ms"] = (time.time() - tts_start) * 1000
            
            # 8. Start playback
            await session.audio_sequencer.play_sequence(output_callback)
            
            # 9. Log total time
            metrics["total_ms"] = (time.time() - start_time) * 1000
            
            session.total_turns += 1
            session.total_latency_ms += metrics["total_ms"]
            
            self._total_turns_processed += 1
            self._total_pipeline_ms += metrics["total_ms"]
            
            logger.info(
                f"Pipeline complete ({metrics['total_ms']:.0f}ms): "
                f"ASR={metrics['asr_ms']:.0f}ms, "
                f"LLM={metrics['llm_ms']:.0f}ms, "
                f"TTS={metrics['tts_ms']:.0f}ms"
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            metrics["error"] = str(e)
            return metrics
            
        finally:
            session.is_processing = False
    
    async def _delayed_filler(
        self,
        session: CallSession,
        delay_ms: int,
    ) -> None:
        """
        Play filler if response is delayed.
        
        Args:
            session: Call session
            delay_ms: Delay before playing filler
        """
        try:
            await asyncio.sleep(delay_ms / 1000)
            
            # Get and play filler
            phrase, audio = self._filler.get_random_filler("searching")
            
            logger.debug(f"Playing delayed filler: {phrase.text}")
            
            if audio:
                await session.audio_sequencer.add_segment(
                    audio,
                    speaker="sara",
                    priority=SegmentPriority.LOW,
                    text=phrase.text,
                )
                
        except asyncio.CancelledError:
            # Filler cancelled because response arrived
            pass
    
    async def handle_barge_in(self, session: CallSession) -> None:
        """
        Handle user barge-in (interruption).
        
        Stops current audio playback immediately.
        
        Args:
            session: Call session
        """
        logger.info(f"Barge-in detected: {session.call_control_id}")
        
        # Stop audio sequencer
        session.audio_sequencer.stop()
        
        # Reset for next turn
        session.audio_sequencer.reset()
        session.is_speaking = True
    
    def end_session(self, call_control_id: str) -> dict[str, Any]:
        """
        End a call session.
        
        Args:
            call_control_id: Session identifier
        
        Returns:
            Session summary metrics
        """
        session = self._sessions.pop(call_control_id, None)
        
        if not session:
            return {"error": "Session not found"}
        
        duration_s = time.time() - session.start_time
        
        summary = {
            "call_control_id": call_control_id,
            "duration_seconds": duration_s,
            "total_turns": session.total_turns,
            "average_latency_ms": session.get_average_latency(),
            "conversation_length": len(session.conversation_history),
        }
        
        logger.info(
            f"Session ended: {call_control_id}, "
            f"duration={duration_s:.1f}s, turns={session.total_turns}"
        )
        
        return summary
    
    async def generate_greeting(self, session: CallSession) -> bytes:
        """
        Generate greeting audio for new call.
        
        Args:
            session: Call session
        
        Returns:
            Greeting audio bytes
        """
        greeting_text = "مرحباً! أنا سارة من عيادة نكسوس مراكل. كيف أقدر أساعدك اليوم؟"
        
        audio = await self._tts.synthesize(greeting_text, Voice.SARA)
        
        session.greeting_sent = True
        session.add_message("sara", greeting_text)
        
        logger.info("Greeting generated")
        return audio
    
    def get_stats(self) -> dict[str, Any]:
        """Get pipeline performance statistics."""
        avg_latency = 0.0
        if self._total_turns_processed > 0:
            avg_latency = self._total_pipeline_ms / self._total_turns_processed
        
        return {
            "total_turns": self._total_turns_processed,
            "average_pipeline_ms": avg_latency,
            "active_sessions": len(self._sessions),
            "services": {
                "vad": self._vad.get_current_state(),
                "asr": self._asr.get_stats(),
                "llm": self._llm.get_stats(),
                "tts": self._tts.get_stats(),
                "filler": self._filler.get_stats(),
            },
        }
    
    async def shutdown(self) -> None:
        """Shutdown all services."""
        # End all sessions
        for call_id in list(self._sessions.keys()):
            self.end_session(call_id)
        
        # Shutdown services
        await asyncio.gather(
            self._vad.shutdown(),
            self._asr.shutdown(),
            self._llm.shutdown(),
            self._tts.shutdown(),
            self._filler.shutdown(),
        )
        
        self._is_initialized = False
        logger.info("PipelineService shutdown")


# Singleton instance
_pipeline_service: PipelineService | None = None


def get_pipeline_service() -> PipelineService:
    """Get the pipeline service singleton instance."""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service
