"""
Nexus Miracle - Interruption Service

Handles custom interruption behavior:
1. Detects when user speaks during assistant's turn
2. Stops assistant's speech immediately
3. Accumulates user's speech until truly finished
4. Plays "تفضل" (please speak) only after extended pause
5. Processes all accumulated speech as ONE request
"""

import asyncio
import time
from enum import Enum
from typing import Optional
from loguru import logger


class InterruptionState(Enum):
    """States for interruption handling."""
    IDLE = "idle"  # Waiting for user to speak
    ASSISTANT_SPEAKING = "assistant_speaking"  # Assistant is talking
    INTERRUPTED = "interrupted"  # User interrupted, accumulating speech
    ACCUMULATING = "accumulating"  # Continuing to accumulate user speech
    SILENCE_DETECTED = "silence_detected"  # Brief silence during user speech


class InterruptionService:
    """
    Manages interruption flow for phone calls.
    
    Flow:
    1. User speaks during assistant's response
    2. Clear playback queue immediately
    3. Set state to INTERRUPTED
    4. Continue accumulating ALL speech
    5. After LONG silence (e.g., 1.5s), play "تفضل" if user seems paused
    6. After final silence, process ALL accumulated speech as one request
    """
    
    # Interruption phrases (Arabic)
    INTERRUPTION_PHRASES = [
        "تفضل",
        "نعم",
    ]
    
    # Timing configuration (in seconds)
    PAUSE_THRESHOLD = 0.8  # Silence duration to consider user paused
    FINAL_SILENCE_THRESHOLD = 1.5  # Silence duration to consider user done
    
    def __init__(self):
        """Initialize the interruption service."""
        self._states: dict[str, InterruptionState] = {}
        self._interruption_count: dict[str, int] = {}
        self._current_phrase_index: dict[str, int] = {}
        
        # Timing tracking
        self._last_speech_time: dict[str, float] = {}
        self._interruption_start_time: dict[str, float] = {}
        
        # Track if we already said "تفضل" for this interruption
        self._tafaddal_played: dict[str, bool] = {}
        
        # Track speech segments count during interruption
        self._speech_segments: dict[str, int] = {}
        
    def create_session(self, call_control_id: str) -> None:
        """
        Initialize interruption tracking for a new call.
        
        Args:
            call_control_id: Unique call identifier
        """
        self._states[call_control_id] = InterruptionState.IDLE
        self._interruption_count[call_control_id] = 0
        self._current_phrase_index[call_control_id] = 0
        self._last_speech_time[call_control_id] = 0
        self._interruption_start_time[call_control_id] = 0
        self._tafaddal_played[call_control_id] = False
        self._speech_segments[call_control_id] = 0
        logger.debug(f"Interruption session created for {call_control_id}")
    
    def get_state(self, call_control_id: str) -> InterruptionState:
        """Get current interruption state for a call."""
        return self._states.get(call_control_id, InterruptionState.IDLE)
    
    def set_assistant_speaking(self, call_control_id: str) -> None:
        """Mark that assistant is now speaking."""
        self._states[call_control_id] = InterruptionState.ASSISTANT_SPEAKING
        self._tafaddal_played[call_control_id] = False
        self._speech_segments[call_control_id] = 0
        logger.debug(f"[{call_control_id}] -> ASSISTANT_SPEAKING")
    
    def set_idle(self, call_control_id: str) -> None:
        """Mark that conversation is idle (waiting for user)."""
        self._states[call_control_id] = InterruptionState.IDLE
        self._tafaddal_played[call_control_id] = False
        self._speech_segments[call_control_id] = 0
        logger.debug(f"[{call_control_id}] -> IDLE")
    
    def should_handle_interruption(self, call_control_id: str) -> bool:
        """
        Check if we should handle a NEW interruption.
        
        Only returns True the FIRST time user speaks during assistant's turn.
        Subsequent speech during the same interruption returns False.
        """
        state = self.get_state(call_control_id)
        return state == InterruptionState.ASSISTANT_SPEAKING
    
    def is_in_interruption_mode(self, call_control_id: str) -> bool:
        """
        Check if we're currently in interruption mode (accumulating speech).
        """
        state = self.get_state(call_control_id)
        return state in (
            InterruptionState.INTERRUPTED,
            InterruptionState.ACCUMULATING,
            InterruptionState.SILENCE_DETECTED,
        )
    
    def start_interruption(self, call_control_id: str) -> None:
        """
        Start an interruption - user spoke during assistant's turn.
        
        Does NOT return a phrase - we wait until user pauses.
        """
        self._states[call_control_id] = InterruptionState.INTERRUPTED
        self._interruption_count[call_control_id] = \
            self._interruption_count.get(call_control_id, 0) + 1
        self._last_speech_time[call_control_id] = time.time()
        self._interruption_start_time[call_control_id] = time.time()
        self._speech_segments[call_control_id] = 1
        
        logger.info(f"🛑 [{call_control_id}] Interruption started - accumulating speech")
    
    def on_speech_detected(self, call_control_id: str) -> None:
        """
        Called when speech is detected during interruption mode.
        
        Updates timing and resets silence detection.
        """
        state = self.get_state(call_control_id)
        
        if state == InterruptionState.SILENCE_DETECTED:
            # User resumed speaking after brief pause
            self._states[call_control_id] = InterruptionState.ACCUMULATING
            self._speech_segments[call_control_id] = \
                self._speech_segments.get(call_control_id, 0) + 1
        
        self._last_speech_time[call_control_id] = time.time()
    
    def on_speech_ended(self, call_control_id: str) -> dict:
        """
        Called when VAD detects end of speech during interruption.
        
        Returns:
            dict with:
            - should_wait: True if we should wait longer for more speech
            - should_say_tafaddal: True if we should play "تفضل"
            - should_process: True if we should process accumulated speech
            - phrase: The phrase to say if should_say_tafaddal is True
        """
        state = self.get_state(call_control_id)
        
        if state not in (
            InterruptionState.INTERRUPTED,
            InterruptionState.ACCUMULATING,
            InterruptionState.SILENCE_DETECTED,
        ):
            return {
                "should_wait": False,
                "should_say_tafaddal": False,
                "should_process": True,
                "phrase": None,
            }
        
        self._states[call_control_id] = InterruptionState.SILENCE_DETECTED
        
        # Always wait for more speech initially
        return {
            "should_wait": True,
            "should_say_tafaddal": False,
            "should_process": False,
            "phrase": None,
        }
    
    def check_silence_duration(self, call_control_id: str) -> dict:
        """
        Check how long the user has been silent.
        
        Called periodically to decide what action to take.
        
        Returns:
            dict with:
            - should_wait: True if still waiting
            - should_say_tafaddal: True if should play "تفضل"
            - should_process: True if should process speech
            - phrase: The phrase to say
        """
        state = self.get_state(call_control_id)
        
        if state not in (
            InterruptionState.INTERRUPTED,
            InterruptionState.ACCUMULATING,
            InterruptionState.SILENCE_DETECTED,
        ):
            return {
                "should_wait": False,
                "should_say_tafaddal": False,
                "should_process": False,
                "phrase": None,
            }
        
        last_speech = self._last_speech_time.get(call_control_id, 0)
        silence_duration = time.time() - last_speech
        
        # If user has been silent for final threshold, process speech
        if silence_duration >= self.FINAL_SILENCE_THRESHOLD:
            segments = self._speech_segments.get(call_control_id, 0)
            logger.info(
                f"✅ [{call_control_id}] User finished speaking. "
                f"Segments: {segments}, Silence: {silence_duration:.1f}s"
            )
            self._states[call_control_id] = InterruptionState.IDLE
            return {
                "should_wait": False,
                "should_say_tafaddal": False,
                "should_process": True,
                "phrase": None,
            }
        
        # If user paused briefly and we haven't said "تفضل" yet
        if (silence_duration >= self.PAUSE_THRESHOLD and 
            not self._tafaddal_played.get(call_control_id, False)):
            
            idx = self._current_phrase_index.get(call_control_id, 0)
            phrase = self.INTERRUPTION_PHRASES[idx % len(self.INTERRUPTION_PHRASES)]
            self._current_phrase_index[call_control_id] = idx + 1
            self._tafaddal_played[call_control_id] = True
            
            logger.info(f"💬 [{call_control_id}] Saying: {phrase}")
            
            return {
                "should_wait": True,
                "should_say_tafaddal": True,
                "should_process": False,
                "phrase": phrase,
            }
        
        # Still waiting
        return {
            "should_wait": True,
            "should_say_tafaddal": False,
            "should_process": False,
            "phrase": None,
        }
    
    def get_interruption_count(self, call_control_id: str) -> int:
        """Get number of times user has interrupted in this call."""
        return self._interruption_count.get(call_control_id, 0)
    
    def end_session(self, call_control_id: str) -> dict:
        """End interruption tracking for a call."""
        stats = {
            "interruption_count": self._interruption_count.get(call_control_id, 0),
        }
        
        # Cleanup
        self._states.pop(call_control_id, None)
        self._interruption_count.pop(call_control_id, None)
        self._current_phrase_index.pop(call_control_id, None)
        self._last_speech_time.pop(call_control_id, None)
        self._interruption_start_time.pop(call_control_id, None)
        self._tafaddal_played.pop(call_control_id, None)
        self._speech_segments.pop(call_control_id, None)
        
        logger.debug(f"Interruption session ended for {call_control_id}: {stats}")
        return stats


# Singleton instance
_interruption_service: InterruptionService | None = None


def get_interruption_service() -> InterruptionService:
    """Get the interruption service singleton instance."""
    global _interruption_service
    if _interruption_service is None:
        _interruption_service = InterruptionService()
    return _interruption_service
