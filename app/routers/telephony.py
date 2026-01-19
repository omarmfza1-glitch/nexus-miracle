"""
Nexus Miracle - Telephony Router

Telnyx webhook handlers and WebSocket endpoint for real-time audio streaming.
Handles incoming calls, bidirectional audio, and call lifecycle events.
"""

import asyncio
import base64
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, status
from loguru import logger
from pydantic import BaseModel

from app.config import get_settings
from app.services.audio_service import get_audio_processor
from app.services.call_service import get_call_service
from app.services.telnyx_service import get_telnyx_service
from app.utils.audio_buffer import AudioBuffer, PlaybackQueue

router = APIRouter()

# Store active WebSocket connections
_active_connections: dict[str, WebSocket] = {}
_playback_queues: dict[str, PlaybackQueue] = {}


# ===========================================
# Request/Response Models
# ===========================================

class TelnyxWebhookPayload(BaseModel):
    """Telnyx webhook event payload."""
    
    event_type: str | None = None
    id: str | None = None
    occurred_at: str | None = None
    payload: dict[str, Any] | None = None
    record_type: str | None = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    
    status: str
    message: str


# ===========================================
# Webhook Endpoints
# ===========================================

@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Telnyx Webhook Handler",
    description="Receives and processes Telnyx telephony events.",
)
async def handle_telnyx_webhook(request: Request) -> dict[str, str]:
    """
    Handle incoming Telnyx webhook events.
    
    Supported events:
        - call.initiated: New incoming call
        - call.answered: Call was answered
        - call.hangup: Call ended
        - streaming.started: Media streaming started
        - streaming.stopped: Media streaming stopped
        - call.dtmf.received: DTMF tone received
    """
    # Parse raw JSON for nested event handling
    body = await request.json()
    
    # Telnyx sends events in data.payload structure
    data = body.get("data", body)
    event_type = data.get("event_type", "")
    payload = data.get("payload", {})
    
    call_control_id = payload.get("call_control_id", "")
    caller_phone = payload.get("from", "")
    called_phone = payload.get("to", "")
    
    logger.info(f"Webhook received: {event_type} for call {call_control_id}")
    logger.debug(f"Webhook payload: {json.dumps(data, default=str)[:500]}")
    
    settings = get_settings()
    telnyx = get_telnyx_service()
    call_service = get_call_service()
    
    try:
        # Handle different event types
        if event_type == "call.initiated":
            # New incoming call - create session and answer
            logger.info(f"📞 Incoming call from {caller_phone} to {called_phone}")
            logger.info(f"📋 Full payload: {json.dumps(payload, default=str)}")
            
            # Validate call_control_id
            if not call_control_id:
                logger.error("❌ Missing call_control_id in payload!")
                return {
                    "status": "error",
                    "message": "Missing call_control_id",
                }
            
            # Create call session
            await call_service.create_session(
                call_control_id=call_control_id,
                caller_phone=caller_phone,
                called_phone=called_phone,
            )
            
            # Build WebSocket URL for media streaming
            # Use the configured webhook base URL
            webhook_base = settings.webhook_base_url or "https://nexus-miracle-production.up.railway.app"
            stream_url = f"{webhook_base.replace('https://', 'wss://').replace('http://', 'ws://')}/api/telephony/media/{call_control_id}"
            
            logger.info(f"🔗 Stream URL: {stream_url}")
            
            # Answer the call and start media streaming
            try:
                await telnyx.initialize()
                await telnyx.answer_call(
                    call_control_id=call_control_id,
                    stream_url=stream_url,
                )
                logger.info(f"✅ Call answered, streaming to {stream_url}")
            except Exception as answer_error:
                logger.exception(f"❌ Failed to answer call: {answer_error}")
                # Don't raise - return error response
                return {
                    "status": "error",
                    "message": f"Failed to answer: {str(answer_error)}",
                }
            
        elif event_type == "call.answered":
            # Call was answered - greeting will be sent via WebSocket
            logger.info(f"📱 Call answered: {call_control_id}")
            
        elif event_type == "streaming.started":
            # Media streaming started
            logger.info(f"🎙️ Media streaming started: {call_control_id}")
            
        elif event_type == "streaming.stopped":
            # Media streaming stopped
            logger.info(f"🔇 Media streaming stopped: {call_control_id}")
            
        elif event_type == "call.hangup":
            # Call ended - cleanup
            hangup_cause = payload.get("hangup_cause", "unknown")
            logger.info(f"📴 Call ended: {call_control_id}, cause: {hangup_cause}")
            
            # End session and log
            summary = await call_service.end_session(call_control_id)
            
            # Cleanup WebSocket if exists
            if call_control_id in _active_connections:
                del _active_connections[call_control_id]
            if call_control_id in _playback_queues:
                del _playback_queues[call_control_id]
            
            logger.info(f"📊 Session summary: {summary}")
            
        elif event_type == "call.dtmf.received":
            # DTMF tone received
            digit = payload.get("digit", "")
            logger.info(f"🔢 DTMF received: {digit} on call {call_control_id}")
            # TODO: Implement IVR menu handling
            
        else:
            logger.debug(f"Unhandled event type: {event_type}")
        
        return {
            "status": "ok",
            "message": f"Processed: {event_type}",
        }
        
    except Exception as e:
        logger.exception(f"Error handling webhook: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


@router.post(
    "/answer",
    response_model=WebhookResponse,
    summary="Answer Incoming Call",
    description="Answers an incoming call and initiates audio streaming.",
)
async def answer_call(call_control_id: str) -> dict[str, str]:
    """Answer an incoming call manually."""
    logger.info(f"Manual answer request: {call_control_id}")
    
    telnyx = get_telnyx_service()
    await telnyx.initialize()
    await telnyx.answer_call(call_control_id)
    
    return {
        "status": "ok",
        "message": f"Answered call: {call_control_id}",
    }


@router.post(
    "/hangup",
    response_model=WebhookResponse,
    summary="Hang Up Call",
    description="Terminates an active call.",
)
async def hangup_call(call_control_id: str) -> dict[str, str]:
    """Hang up an active call."""
    logger.info(f"Hanging up call: {call_control_id}")
    
    telnyx = get_telnyx_service()
    await telnyx.initialize()
    await telnyx.hangup_call(call_control_id)
    
    # End session
    call_service = get_call_service()
    await call_service.end_session(call_control_id)
    
    return {
        "status": "ok",
        "message": f"Hung up call: {call_control_id}",
    }


# ===========================================
# WebSocket Media Endpoint
# ===========================================

@router.websocket("/media/{call_control_id}")
async def media_websocket(websocket: WebSocket, call_control_id: str) -> None:
    """
    WebSocket endpoint for bidirectional audio streaming with Telnyx.
    
    Telnyx sends:
        {
            "event": "media",
            "media": {
                "payload": "<base64 μ-law audio>",
                "track": "inbound"
            }
        }
    
    We send back:
        {
            "event": "media",
            "media": {
                "payload": "<base64 μ-law audio>",
                "track": "outbound"
            }
        }
    """
    await websocket.accept()
    
    logger.info(f"🔌 WebSocket ACCEPTED for call: {call_control_id}")
    
    # Store connection
    _active_connections[call_control_id] = websocket
    _playback_queues[call_control_id] = PlaybackQueue(chunk_size=160)
    
    # Get services
    call_service = get_call_service()
    audio_processor = get_audio_processor()
    
    # Audio buffer for incoming speech
    audio_buffer = AudioBuffer(sample_rate=16000)
    
    # Get or wait for session
    session = call_service.get_session(call_control_id)
    if not session:
        logger.warning(f"No session found for {call_control_id}, creating one")
        session = await call_service.create_session(
            call_control_id=call_control_id,
            caller_phone="unknown",
            called_phone="unknown",
        )
    
    # Flag for greeting sent
    greeting_sent = False
    
    # === SEND GREETING IMMEDIATELY ON WEBSOCKET ACCEPT ===
    # Don't await greeting here - it may fail and crash the connection
    # Instead, we'll send greeting on "connected" or "start" event
    logger.info(f"🔌 WebSocket ready for call: {call_control_id}, will send greeting on stream events")
    
    # Silence checker task for interruption handling
    silence_checker_task: asyncio.Task | None = None
    
    async def check_silence_loop():
        """Periodically check silence duration during interruption."""
        while True:
            try:
                await asyncio.sleep(0.2)  # Check every 200ms
                
                result = await call_service.check_interruption_silence(call_control_id)
                
                if result["should_say_tafaddal"] and result["phrase_audio"]:
                    # Queue "تفضل" audio
                    telnyx_audio = audio_processor.ai_to_telnyx(result["phrase_audio"])
                    playback_queue = _playback_queues.get(call_control_id)
                    if playback_queue:
                        await playback_queue.enqueue(telnyx_audio)
                        logger.info(f"💬 [{call_control_id}] تفضل queued")
                
                elif result["should_process"] and result["response_audio"]:
                    # User is done - queue the full response
                    response_audio = result["response_audio"]
                    telnyx_audio = audio_processor.ai_to_telnyx(response_audio)
                    playback_queue = _playback_queues.get(call_control_id)
                    if playback_queue:
                        call_service.set_assistant_speaking(call_control_id, True)
                        await playback_queue.enqueue(telnyx_audio)
                        logger.info(f"🔊 [{call_control_id}] Full response queued: {len(response_audio)} bytes")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Silence checker error: {e}")
    
    try:
        # Start playback sender task
        playback_task = asyncio.create_task(
            _send_playback_audio(websocket, call_control_id, audio_processor, call_service)
        )
        
        # Start silence checker task
        silence_checker_task = asyncio.create_task(check_silence_loop())
        
        while True:
            # Receive message from Telnyx
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            
            event = message.get("event", "")
            logger.debug(f"📨 [{call_control_id}] WebSocket event: {event}")
            
            if event == "connected":
                logger.info(f"📡 Telnyx stream connected: {call_control_id}")
                
                # Send greeting on connect if not sent yet
                if not greeting_sent:
                    try:
                        call_service.set_assistant_speaking(call_control_id, True)
                        greeting_audio = await call_service.handle_call_answered(call_control_id)
                        telnyx_audio = audio_processor.ai_to_telnyx(greeting_audio)
                        playback_queue = _playback_queues.get(call_control_id)
                        if playback_queue:
                            await playback_queue.enqueue(telnyx_audio)
                        greeting_sent = True
                        logger.info(f"🎤 Greeting queued on connect: {len(greeting_audio)} bytes")
                    except Exception as e:
                        logger.error(f"Failed to send greeting on connect: {e}")
                
            elif event == "start":
                # Stream started - send greeting if not already sent
                logger.info(f"▶️ Stream started: {call_control_id}")
                
                if not greeting_sent:
                    try:
                        call_service.set_assistant_speaking(call_control_id, True)
                        greeting_audio = await call_service.handle_call_answered(call_control_id)
                        telnyx_audio = audio_processor.ai_to_telnyx(greeting_audio)
                        playback_queue = _playback_queues.get(call_control_id)
                        if playback_queue:
                            await playback_queue.enqueue(telnyx_audio)
                        greeting_sent = True
                        logger.info(f"🎤 Greeting queued on start: {len(greeting_audio)} bytes")
                    except Exception as e:
                        logger.error(f"Failed to send greeting on start: {e}")
                
            elif event == "media":
                # Audio data from caller
                media = message.get("media", {})
                track = media.get("track", "")
                
                # Fallback: send greeting on first media if not sent yet
                if not greeting_sent:
                    try:
                        call_service.set_assistant_speaking(call_control_id, True)
                        greeting_audio = await call_service.handle_call_answered(call_control_id)
                        telnyx_audio = audio_processor.ai_to_telnyx(greeting_audio)
                        playback_queue = _playback_queues.get(call_control_id)
                        if playback_queue:
                            await playback_queue.enqueue(telnyx_audio)
                        greeting_sent = True
                        logger.info(f"🎤 Greeting queued on first media: {len(greeting_audio)} bytes")
                    except Exception as e:
                        logger.error(f"Failed to send greeting on media: {e}")
                
                if track == "inbound":
                    # Decode base64 μ-law audio
                    payload_b64 = media.get("payload", "")
                    ulaw_audio = base64.b64decode(payload_b64)
                    
                    # Convert to AI format (PCM 16kHz)
                    pcm_audio = audio_processor.telnyx_to_ai(ulaw_audio)
                    
                    # Process through call service
                    result = await call_service.process_audio_chunk(
                        call_control_id=call_control_id,
                        audio_bytes=pcm_audio,
                    )
                    
                    # Check if interruption started - clear playback immediately
                    if result.get("clear_playback"):
                        playback_queue = _playback_queues.get(call_control_id)
                        if playback_queue:
                            playback_queue.clear()
                        call_service.set_assistant_speaking(call_control_id, False)
                        logger.info(f"🛑 [{call_control_id}] Playback cleared, listening to user")
                    
                    # If response audio generated (non-interruption case), queue it
                    elif result.get("response_audio"):
                        response_audio = result["response_audio"]
                        telnyx_audio = audio_processor.ai_to_telnyx(response_audio)
                        
                        playback_queue = _playback_queues.get(call_control_id)
                        if playback_queue:
                            # Mark assistant as speaking before queueing response
                            call_service.set_assistant_speaking(call_control_id, True)
                            await playback_queue.enqueue(telnyx_audio)
                        
                        logger.info(f"🔊 Response queued: {len(response_audio)} bytes")
                
            elif event == "stop":
                logger.info(f"⏹️ Stream stopped: {call_control_id}")
                break
                
            else:
                logger.debug(f"Unknown event: {event}")
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {call_control_id}")
        
    except Exception as e:
        logger.exception(f"WebSocket error for {call_control_id}: {e}")
        
    finally:
        # Cleanup
        playback_task.cancel()
        if silence_checker_task:
            silence_checker_task.cancel()
        
        if call_control_id in _active_connections:
            del _active_connections[call_control_id]
        if call_control_id in _playback_queues:
            del _playback_queues[call_control_id]
        
        logger.info(f"🧹 Cleanup complete for: {call_control_id}")


async def _send_playback_audio(
    websocket: WebSocket,
    call_control_id: str,
    audio_processor,
    call_service,
) -> None:
    """
    Background task to send queued audio to Telnyx.
    
    Sends audio chunks at 20ms intervals to maintain real-time streaming.
    Notifies call_service when playback completes.
    """
    playback_queue = _playback_queues.get(call_control_id)
    if not playback_queue:
        return
    
    # Track if we were previously playing audio
    was_playing = False
    
    try:
        while True:
            # Get next chunk (20ms timeout)
            chunk = await playback_queue.dequeue(timeout=0.02)
            
            if chunk:
                was_playing = True
                
                # Encode as base64
                payload_b64 = base64.b64encode(chunk).decode("utf-8")
                
                # Send to Telnyx
                await websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": payload_b64,
                        "track": "outbound",
                    },
                })
            else:
                # No audio to send
                # If we were playing and now stopped, mark assistant as not speaking
                if was_playing and not playback_queue.is_playing():
                    call_service.set_assistant_speaking(call_control_id, False)
                    was_playing = False
                    logger.debug(f"🔇 Playback complete for: {call_control_id}")
                
                # Small sleep to avoid busy loop
                await asyncio.sleep(0.01)
                
    except asyncio.CancelledError:
        logger.debug(f"Playback task cancelled: {call_control_id}")
    except Exception as e:
        logger.error(f"Playback error for {call_control_id}: {e}")


# ===========================================
# Legacy WebSocket (for backward compatibility)
# ===========================================

@router.websocket("/ws")
async def telephony_websocket(websocket: WebSocket) -> None:
    """Legacy WebSocket endpoint for testing."""
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"Legacy WebSocket connected: {client_id}")
    
    try:
        while True:
            data = await websocket.receive()
            
            if "bytes" in data:
                audio_bytes = data["bytes"]
                logger.debug(f"Received audio: {len(audio_bytes)} bytes")
                await websocket.send_bytes(audio_bytes)
                
            elif "text" in data:
                message = data["text"]
                logger.debug(f"Received message: {message}")
                await websocket.send_json({
                    "type": "ack",
                    "message": "Received",
                })
                
    except WebSocketDisconnect:
        logger.info(f"Legacy WebSocket disconnected: {client_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")


@router.get(
    "",
    summary="Telephony Status",
    description="Returns the current telephony system status.",
)
async def get_telephony_status() -> dict[str, Any]:
    """Get telephony system status."""
    call_service = get_call_service()
    
    return {
        "status": "ok",
        "active_calls": call_service.get_active_call_count(),
        "websocket_connections": len(_active_connections),
        "telnyx_connected": True,
    }
