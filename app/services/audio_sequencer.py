"""
Nexus Miracle - Audio Sequencer

Manages audio playback queue with barge-in support.
Handles chunked audio delivery for real-time streaming.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

from loguru import logger


class SegmentPriority(int, Enum):
    """Priority levels for audio segments."""
    
    LOW = 0        # Background/filler
    NORMAL = 1     # Regular response
    HIGH = 2       # Important/empathy
    CRITICAL = 3   # System messages


@dataclass
class AudioSegment:
    """Single audio segment for playback."""
    
    audio: bytes
    speaker: str
    priority: SegmentPriority = SegmentPriority.NORMAL
    segment_id: str = ""
    text: str = ""
    
    def __lt__(self, other: "AudioSegment") -> bool:
        """Compare by priority (higher priority = processed first)."""
        return self.priority > other.priority


class AudioSequencer:
    """
    Audio playback queue manager.
    
    Features:
    - Priority-based queue
    - Chunked playback (20ms intervals)
    - Barge-in support (immediate stop)
    - Non-overlapping audio delivery
    
    Usage:
        sequencer = AudioSequencer()
        await sequencer.add_segment(audio_bytes, "sara")
        await sequencer.play_sequence(send_callback)
    """
    
    def __init__(self, chunk_duration_ms: int = 20) -> None:
        """
        Initialize the audio sequencer.
        
        Args:
            chunk_duration_ms: Duration of each audio chunk in milliseconds
        """
        self._queue: asyncio.PriorityQueue[AudioSegment] = asyncio.PriorityQueue()
        self._chunk_duration_ms = chunk_duration_ms
        
        # State flags
        self._is_playing = False
        self._should_stop = False
        self._is_paused = False
        
        # Current segment info
        self._current_segment: AudioSegment | None = None
        self._current_position = 0
        
        # Statistics
        self._total_segments = 0
        self._total_bytes_played = 0
        self._barge_in_count = 0
        
        # Sample rate for chunk calculation (16kHz, 16-bit mono)
        self._sample_rate = 16000
        self._bytes_per_sample = 2
        self._bytes_per_chunk = int(
            self._sample_rate * self._bytes_per_sample * 
            self._chunk_duration_ms / 1000
        )
        
        logger.info(f"AudioSequencer created: {chunk_duration_ms}ms chunks")
    
    async def add_segment(
        self,
        audio: bytes,
        speaker: str = "sara",
        priority: int | SegmentPriority = SegmentPriority.NORMAL,
        text: str = "",
    ) -> None:
        """
        Add an audio segment to the playback queue.
        
        Args:
            audio: Audio bytes (PCM 16-bit 16kHz)
            speaker: Speaker name (sara/nexus)
            priority: Playback priority (higher = sooner)
            text: Original text (for logging)
        """
        if isinstance(priority, int):
            priority = SegmentPriority(priority)
        
        segment = AudioSegment(
            audio=audio,
            speaker=speaker,
            priority=priority,
            segment_id=f"seg_{self._total_segments}",
            text=text[:50] if text else "",
        )
        
        await self._queue.put(segment)
        self._total_segments += 1
        
        logger.debug(
            f"Queued segment: {segment.segment_id}, "
            f"speaker={speaker}, bytes={len(audio)}, priority={priority.name}"
        )
    
    async def play_sequence(
        self,
        output_callback: Callable[[bytes], Awaitable[None]],
    ) -> None:
        """
        Play all queued audio segments.
        
        Args:
            output_callback: Async function to send audio chunks
        """
        self._is_playing = True
        self._should_stop = False
        
        logger.debug("Starting audio playback sequence")
        
        try:
            while not self._queue.empty() and not self._should_stop:
                # Get next segment
                self._current_segment = await self._queue.get()
                self._current_position = 0
                
                logger.debug(
                    f"Playing: {self._current_segment.segment_id}, "
                    f"speaker={self._current_segment.speaker}"
                )
                
                # Play in chunks
                audio = self._current_segment.audio
                while self._current_position < len(audio) and not self._should_stop:
                    # Wait if paused
                    while self._is_paused and not self._should_stop:
                        await asyncio.sleep(0.01)
                    
                    if self._should_stop:
                        break
                    
                    # Get next chunk
                    chunk_end = min(
                        self._current_position + self._bytes_per_chunk,
                        len(audio)
                    )
                    chunk = audio[self._current_position:chunk_end]
                    
                    # Send chunk
                    await output_callback(chunk)
                    
                    self._current_position = chunk_end
                    self._total_bytes_played += len(chunk)
                    
                    # Wait for chunk duration
                    await asyncio.sleep(self._chunk_duration_ms / 1000)
                
                self._current_segment = None
                
        except asyncio.CancelledError:
            logger.debug("Audio playback cancelled")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self._is_playing = False
            self._current_segment = None
            logger.debug("Audio playback sequence ended")
    
    def stop(self) -> None:
        """
        Stop playback immediately (barge-in).
        
        Clears the queue and stops current playback.
        """
        self._should_stop = True
        self._barge_in_count += 1
        
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info(f"Barge-in: playback stopped (total: {self._barge_in_count})")
    
    def pause(self) -> None:
        """Pause playback."""
        self._is_paused = True
        logger.debug("Playback paused")
    
    def resume(self) -> None:
        """Resume playback."""
        self._is_paused = False
        logger.debug("Playback resumed")
    
    def reset(self) -> None:
        """Reset sequencer state for new conversation turn."""
        self._should_stop = False
        self._is_paused = False
        self._current_segment = None
        self._current_position = 0
        
        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.debug("AudioSequencer reset")
    
    @property
    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        return self._is_playing
    
    @property
    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return self._is_paused
    
    @property
    def queue_size(self) -> int:
        """Get number of segments in queue."""
        return self._queue.qsize()
    
    def get_current_progress(self) -> dict:
        """Get current playback progress."""
        if not self._current_segment:
            return {
                "is_playing": False,
                "segment_id": None,
                "progress_percent": 0,
            }
        
        total = len(self._current_segment.audio)
        progress = (self._current_position / total * 100) if total > 0 else 0
        
        return {
            "is_playing": True,
            "segment_id": self._current_segment.segment_id,
            "speaker": self._current_segment.speaker,
            "progress_percent": progress,
            "position_bytes": self._current_position,
            "total_bytes": total,
        }
    
    def get_stats(self) -> dict:
        """Get sequencer statistics."""
        return {
            "total_segments": self._total_segments,
            "total_bytes_played": self._total_bytes_played,
            "barge_in_count": self._barge_in_count,
            "queue_size": self.queue_size,
            "is_playing": self._is_playing,
        }


def create_audio_sequencer(chunk_duration_ms: int = 20) -> AudioSequencer:
    """Create a new AudioSequencer instance."""
    return AudioSequencer(chunk_duration_ms)
