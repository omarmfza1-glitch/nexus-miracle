"""
Nexus Miracle - Telnyx Service

Telnyx Call Control API client for managing phone calls.
Handles answering, hanging up, and media forking to WebSocket.
"""

import asyncio
from typing import Any, Optional

import httpx
from loguru import logger

from app.config import get_settings


class TelnyxService:
    """
    Telnyx Call Control API client.
    
    Provides methods for:
    - Answering incoming calls
    - Hanging up calls
    - Forking media to WebSocket for audio streaming
    """
    
    BASE_URL = "https://api.telnyx.com/v2"
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the Telnyx service.
        
        Args:
            api_key: Telnyx API key (or use from settings)
        """
        self._settings = get_settings()
        self._api_key = api_key or self._settings.telnyx_api_key
        
        self._client: Optional[httpx.AsyncClient] = None
        self._is_initialized = False
        
        logger.info("TelnyxService created")
    
    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        if self._is_initialized:
            return
        
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        
        self._is_initialized = True
        logger.info("TelnyxService initialized")
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if not self._client:
            await self.initialize()
        return self._client  # type: ignore
    
    async def answer_call(
        self,
        call_control_id: str,
        webhook_url: Optional[str] = None,
        stream_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Answer an incoming call and optionally start media streaming.
        
        Args:
            call_control_id: Telnyx call control ID
            webhook_url: URL for webhook events (optional)
            stream_url: WebSocket URL for media streaming (optional)
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        payload: dict[str, Any] = {}
        
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        logger.info(f"Answering call: {call_control_id}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/answer",
            json=payload,
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Call answered: {call_control_id}")
        
        # Start media streaming if stream URL provided
        if stream_url:
            await self.start_media_stream(call_control_id, stream_url)
        
        return result
    
    async def start_media_stream(
        self,
        call_control_id: str,
        stream_url: str,
        stream_track: str = "both_tracks",
    ) -> dict[str, Any]:
        """
        Start streaming audio to/from a WebSocket endpoint.
        
        Args:
            call_control_id: Telnyx call control ID
            stream_url: WebSocket URL to stream audio
            stream_track: Which tracks to stream (inbound/outbound/both_tracks)
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        payload = {
            "stream_url": stream_url,
            "stream_track": stream_track,
        }
        
        logger.info(f"Starting media stream for {call_control_id} -> {stream_url}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/streaming_start",
            json=payload,
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Media streaming started: {call_control_id}")
        
        return result
    
    async def stop_media_stream(
        self,
        call_control_id: str,
    ) -> dict[str, Any]:
        """
        Stop streaming audio for a call.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        logger.info(f"Stopping media stream: {call_control_id}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/streaming_stop",
            json={},
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Media streaming stopped: {call_control_id}")
        
        return result
    
    async def hangup_call(
        self,
        call_control_id: str,
    ) -> dict[str, Any]:
        """
        Hang up an active call.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        logger.info(f"Hanging up call: {call_control_id}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/hangup",
            json={},
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Call hung up: {call_control_id}")
        
        return result
    
    async def speak(
        self,
        call_control_id: str,
        text: str,
        voice: str = "female",
        language: str = "ar-SA",
    ) -> dict[str, Any]:
        """
        Speak text on the call using Telnyx TTS.
        
        Note: This uses Telnyx's built-in TTS, not ElevenLabs.
        For high-quality Arabic, use media streaming with our TTS.
        
        Args:
            call_control_id: Telnyx call control ID
            text: Text to speak
            voice: Voice type (male/female)
            language: Language code
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        payload = {
            "payload": text,
            "voice": voice,
            "language": language,
        }
        
        logger.info(f"Speaking on call {call_control_id}: {text[:50]}...")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/speak",
            json=payload,
        )
        
        response.raise_for_status()
        return response.json()
    
    async def play_audio(
        self,
        call_control_id: str,
        audio_url: str,
    ) -> dict[str, Any]:
        """
        Play audio file on the call.
        
        Args:
            call_control_id: Telnyx call control ID
            audio_url: URL of the audio file to play
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        payload = {
            "audio_url": audio_url,
        }
        
        logger.info(f"Playing audio on call {call_control_id}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/playback_start",
            json=payload,
        )
        
        response.raise_for_status()
        return response.json()
    
    async def send_dtmf(
        self,
        call_control_id: str,
        digits: str,
    ) -> dict[str, Any]:
        """
        Send DTMF tones on the call.
        
        Args:
            call_control_id: Telnyx call control ID
            digits: DTMF digits to send (0-9, *, #)
        
        Returns:
            API response data
        """
        client = await self._ensure_client()
        
        payload = {
            "digits": digits,
        }
        
        logger.info(f"Sending DTMF on call {call_control_id}: {digits}")
        
        response = await client.post(
            f"/calls/{call_control_id}/actions/send_dtmf",
            json=payload,
        )
        
        response.raise_for_status()
        return response.json()
    
    async def get_call(
        self,
        call_control_id: str,
    ) -> dict[str, Any]:
        """
        Get call details.
        
        Args:
            call_control_id: Telnyx call control ID
        
        Returns:
            Call details
        """
        client = await self._ensure_client()
        
        response = await client.get(f"/calls/{call_control_id}")
        response.raise_for_status()
        
        return response.json()
    
    async def shutdown(self) -> None:
        """Cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._is_initialized = False
        
        logger.info("TelnyxService shutdown")


# Singleton instance
_telnyx_service: Optional[TelnyxService] = None


def get_telnyx_service() -> TelnyxService:
    """
    Get the Telnyx service singleton instance.
    
    Returns:
        TelnyxService instance
    """
    global _telnyx_service
    if _telnyx_service is None:
        _telnyx_service = TelnyxService()
    return _telnyx_service
