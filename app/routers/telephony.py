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
    greeting_lock = asyncio.Lock()
    
    async def send_greeting_task():
        """Background task to generate and queue greeting."""
        nonlocal greeting_sent
        async with greeting_lock:
            if greeting_sent:
                return
            try:
                logger.info(f"🎤 Generating greeting for: {call_control_id}")
                call_service.set_assistant_speaking(call_control_id, True)
                greeting_audio = await call_service.handle_call_answered(call_control_id)
                
                if greeting_audio and len(greeting_audio) > 0:
                    telnyx_audio = audio_processor.ai_to_telnyx(greeting_audio)
                    playback_queue = _playback_queues.get(call_control_id)
                    if playback_queue:
                        await playback_queue.enqueue(telnyx_audio)
                    greeting_sent = True
                    logger.info(f"✅ Greeting queued: {len(greeting_audio)} bytes -> {len(telnyx_audio)} bytes μ-law")
                else:
                    logger.error(f"❌ Greeting audio is empty for: {call_control_id}")
            except Exception as e:
                logger.exception(f"❌ Failed to generate greeting: {e}")
    
    # Silence checker task for interruption handling
    silence_checker_task: asyncio.Task | None = None
    greeting_task: asyncio.Task | None = None
    
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
        
        # Start greeting task immediately (don't wait for events)
        greeting_task = asyncio.create_task(send_greeting_task())
        
        while True:
            # Receive message from Telnyx
            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)
            
            event = message.get("event", "")
            logger.debug(f"📨 [{call_control_id}] WebSocket event: {event}")
            
            if event == "connected":
                logger.info(f"📡 Telnyx stream connected: {call_control_id}")
                
            elif event == "start":
                logger.info(f"▶️ Stream started: {call_control_id}")
                
            elif event == "media":
                # Audio data from caller
                media = message.get("media", {})
                track = media.get("track", "")
                
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
        if greeting_task:
            greeting_task.cancel()
        
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
    
    Sends audio chunks as fast as possible while maintaining real-time rate.
    Uses adaptive timing to reduce latency.
    """
    import time
    
    playback_queue = _playback_queues.get(call_control_id)
    if not playback_queue:
        return
    
    was_playing = False
    chunks_sent = 0
    start_time = 0.0
    CHUNK_DURATION = 0.020  # Each chunk is 20ms of audio
    
    try:
        while True:
            chunk = await playback_queue.dequeue(timeout=0.015)
            
            if chunk:
                if not was_playing:
                    was_playing = True
                    chunks_sent = 0
                    start_time = time.perf_counter()
                
                chunks_sent += 1
                
                # Encode and send
                payload_b64 = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": payload_b64,
                        "track": "outbound",
                    },
                })
                
                # Adaptive timing: only wait if we're ahead of real-time
                expected_time = chunks_sent * CHUNK_DURATION
                actual_time = time.perf_counter() - start_time
                if actual_time < expected_time - 0.005:  # 5ms buffer
                    await asyncio.sleep(expected_time - actual_time)
                
            else:
                if was_playing and not playback_queue.is_playing():
                    call_service.set_assistant_speaking(call_control_id, False)
                    was_playing = False
                    logger.debug(f"🔇 Playback complete for: {call_control_id}")
                
                await asyncio.sleep(0.01)
                
    except asyncio.CancelledError:
        logger.debug(f"Playback task cancelled: {call_control_id}")
    except Exception as e:
        logger.error(f"Playback error for {call_control_id}: {e}")


# ===========================================
# Web Testing WebSocket (Browser Direct)
# ===========================================

@router.websocket("/web-test")
async def web_test_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for browser-based voice testing.
    
    Receives PCM 16kHz audio from browser, processes it, and returns responses.
    No Telnyx/μ-law conversion needed.
    """
    await websocket.accept()
    session_id = f"web-{id(websocket)}"
    logger.info(f"🌐 Web test session started: {session_id}")
    
    # Get services
    call_service = get_call_service()
    
    # Create session
    try:
        session = await call_service.create_session(
            call_control_id=session_id,
            caller_phone="web-test",
            called_phone="web-test",
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        await websocket.close()
        return
    
    # Track state
    greeting_sent = False
    
    async def send_audio_response(audio_bytes: bytes):
        """Send audio back to browser as base64."""
        if audio_bytes and len(audio_bytes) > 0:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await websocket.send_json({
                "type": "audio",
                "audio": audio_b64,
            })
    
    try:
        # Send greeting immediately
        logger.info(f"🎤 Generating greeting for web: {session_id}")
        call_service.set_assistant_speaking(session_id, True)
        greeting_audio = await call_service.handle_call_answered(session_id)
        
        if greeting_audio and len(greeting_audio) > 0:
            # Send greeting text
            await websocket.send_json({
                "type": "greeting",
                "text": "مرحباً بك في نيكسوس ميراكل. كيف يمكنني مساعدتك اليوم؟",
            })
            # Send greeting audio
            await send_audio_response(greeting_audio)
            greeting_sent = True
            logger.info(f"✅ Greeting sent to web client: {len(greeting_audio)} bytes")
        
        call_service.set_assistant_speaking(session_id, False)
        
        # Main loop - receive and process audio
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            logger.debug(f"📥 [{session_id}] Received message type: {msg_type}")
            
            if msg_type == "audio":
                # Decode audio from browser (PCM 16kHz, Int16)
                audio_b64 = data.get("audio", "")
                audio_bytes = base64.b64decode(audio_b64)
                logger.debug(f"🎤 [{session_id}] Received audio: {len(audio_bytes)} bytes")
                
                # Process audio chunk
                result = await call_service.process_audio_chunk(
                    call_control_id=session_id,
                    audio_bytes=audio_bytes,
                )
                
                # Check for response audio
                if result.get("response_audio"):
                    response_audio = result["response_audio"]
                    
                    # Send transcript
                    await websocket.send_json({
                        "type": "listening",
                    })
                    
                    # Send audio
                    call_service.set_assistant_speaking(session_id, True)
                    await send_audio_response(response_audio)
                    call_service.set_assistant_speaking(session_id, False)
                    
                    logger.info(f"🔊 Response sent to web: {len(response_audio)} bytes")
                    
    except WebSocketDisconnect:
        logger.info(f"🌐 Web test session disconnected: {session_id}")
    except Exception as e:
        logger.exception(f"Web test error: {e}")
    finally:
        # End session
        try:
            call_service.end_session(session_id)
        except:
            pass
        logger.info(f"🧹 Web test cleanup complete: {session_id}")


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
