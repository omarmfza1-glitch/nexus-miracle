"""
Nexus Miracle - Audio Buffer Utility

Accumulates audio chunks for speech processing.
Used to collect audio during speech until VAD detects end of speech.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class AudioBuffer:
    """
    Audio chunk accumulator for speech processing.
    
    Collects audio chunks until speech ends, then provides
    the complete audio for ASR processing.
    """
    
    chunks: list[bytes] = field(default_factory=list)
    total_bytes: int = 0
    sample_rate: int = 16000
    bytes_per_sample: int = 2  # 16-bit audio
    
    def add_chunk(self, chunk: bytes, duration_ms: int = 20) -> None:
        """
        Add an audio chunk to the buffer.
        
        Args:
            chunk: Raw audio bytes
            duration_ms: Duration of the chunk in milliseconds
        """
        self.chunks.append(chunk)
        self.total_bytes += len(chunk)
    
    def get_all_and_clear(self) -> bytes:
        """
        Get all accumulated audio and clear the buffer.
        
        Returns:
            Concatenated audio bytes from all chunks
        """
        if not self.chunks:
            return b""
        
        all_audio = b"".join(self.chunks)
        total_bytes = self.total_bytes
        
        # Clear buffer
        self.chunks.clear()
        self.total_bytes = 0
        
        logger.debug(f"Buffer flushed: {total_bytes} bytes")
        
        return all_audio
    
    def get_duration_ms(self) -> float:
        """
        Get total duration of buffered audio in milliseconds.
        
        Returns:
            Duration in milliseconds
        """
        samples = self.total_bytes // self.bytes_per_sample
        return (samples / self.sample_rate) * 1000
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self.chunks) == 0
    
    def clear(self) -> None:
        """Clear the buffer without returning data."""
        self.chunks.clear()
        self.total_bytes = 0


class PlaybackQueue:
    """
    Async queue for audio playback chunks.
    
    Used to queue synthesized audio for sending to Telnyx.
    """
    
    def __init__(self, chunk_size: int = 160) -> None:
        """
        Initialize the playback queue.
        
        Args:
            chunk_size: Size of each audio chunk in samples
        """
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._chunk_size = chunk_size
        self._is_playing = False
    
    async def enqueue(self, audio: bytes) -> None:
        """
        Add audio to the playback queue.
        
        Splits audio into chunks for streaming.
        
        Args:
            audio: Audio bytes to queue
        """
        # Split into 20ms chunks for streaming
        # At 8kHz μ-law: 160 bytes per 20ms
        chunk_bytes = self._chunk_size
        
        for i in range(0, len(audio), chunk_bytes):
            chunk = audio[i:i + chunk_bytes]
            await self._queue.put(chunk)
        
        self._is_playing = True
        logger.debug(f"Queued {len(audio)} bytes as {len(audio) // chunk_bytes} chunks")
    
    async def dequeue(self, timeout: float = 0.02) -> Optional[bytes]:
        """
        Get the next audio chunk for playback.
        
        Args:
            timeout: Timeout in seconds for waiting
        
        Returns:
            Audio chunk or None if queue is empty/timeout
        """
        try:
            chunk = await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout,
            )
            
            if self._queue.empty():
                self._is_playing = False
            
            return chunk
            
        except asyncio.TimeoutError:
            return None
    
    def is_playing(self) -> bool:
        """Check if there's audio being played."""
        return self._is_playing and not self._queue.empty()
    
    def clear(self) -> None:
        """Clear all pending audio."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self._is_playing = False
    
    @property
    def pending_chunks(self) -> int:
        """Get count of pending chunks."""
        return self._queue.qsize()
