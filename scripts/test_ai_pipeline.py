"""
Phase 5: AI Pipeline Tests

Tests for VAD, ASR, LLM, TTS and full pipeline latency.
Run with: python scripts/test_ai_pipeline.py
"""

import asyncio
import json
import time
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.vad_service import get_vad_service, VADEvent
from app.services.asr_service import get_asr_service
from app.services.llm_service import get_llm_service, ConversationContext
from app.services.tts_service import get_tts_service, Voice
from app.services.pipeline_service import get_pipeline_service

# Test results
results = []


def log_result(test_id: str, passed: bool, details: str = "", latency_ms: float = 0):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    latency_str = f" [{latency_ms:.0f}ms]" if latency_ms > 0 else ""
    print(f"{status} - {test_id}{latency_str}: {details}")
    results.append({
        "test": test_id,
        "passed": passed,
        "details": details,
        "latency_ms": latency_ms,
    })


def generate_speech_audio(duration_ms: int = 1000, frequency: float = 440) -> bytes:
    """Generate synthetic speech-like audio (sine wave with noise)."""
    sample_rate = 16000
    samples = int(sample_rate * duration_ms / 1000)
    
    # Generate sine wave with amplitude modulation
    t = np.linspace(0, duration_ms / 1000, samples)
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Add some variation
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 5 * t)
    audio = audio * modulation
    
    # Add noise
    noise = np.random.normal(0, 0.1, samples)
    audio = audio + noise
    
    # Scale to int16
    audio = (audio * 0.5 * 32767).astype(np.int16)
    return audio.tobytes()


def generate_silence(duration_ms: int = 500) -> bytes:
    """Generate silence audio."""
    sample_rate = 16000
    samples = int(sample_rate * duration_ms / 1000)
    audio = np.zeros(samples, dtype=np.int16)
    return audio.tobytes()


# ===========================================
# VAD Tests
# ===========================================

async def test_t5_1_vad_speech_detection():
    """T5.1: VAD - Speech Detection"""
    print("\n" + "="*50)
    print("T5.1: VAD - Speech Detection")
    print("="*50)
    
    vad = get_vad_service()
    await vad.initialize()
    vad.reset()
    
    # Generate speech audio
    speech_audio = generate_speech_audio(500)
    
    # Process in chunks
    chunk_size = 640  # 20ms at 16kHz
    events = []
    
    for i in range(0, len(speech_audio), chunk_size):
        chunk = speech_audio[i:i+chunk_size]
        if len(chunk) == chunk_size:
            event = vad.process_chunk(chunk)
            events.append(event)
    
    # Check for speech events
    has_speech = any(e in (VADEvent.SPEECH_START, VADEvent.SPEECH_CONTINUE) for e in events)
    
    if has_speech:
        log_result("T5.1", True, f"Speech detected, events: {len(events)}")
    else:
        log_result("T5.1", False, "No speech detected")


async def test_t5_2_vad_silence_detection():
    """T5.2: VAD - Silence Detection"""
    print("\n" + "="*50)
    print("T5.2: VAD - Silence Detection")
    print("="*50)
    
    vad = get_vad_service()
    await vad.initialize()
    vad.reset()
    
    # Generate silence
    silence_audio = generate_silence(500)
    
    # Process in chunks
    chunk_size = 640
    speech_starts = 0
    
    for i in range(0, len(silence_audio), chunk_size):
        chunk = silence_audio[i:i+chunk_size]
        if len(chunk) == chunk_size:
            event = vad.process_chunk(chunk)
            if event == VADEvent.SPEECH_START:
                speech_starts += 1
    
    if speech_starts == 0:
        log_result("T5.2", True, "No false positives")
    else:
        log_result("T5.2", False, f"False positives: {speech_starts}")


async def test_t5_3_vad_latency():
    """T5.3: VAD - Latency"""
    print("\n" + "="*50)
    print("T5.3: VAD - Latency (<5ms per chunk)")
    print("="*50)
    
    vad = get_vad_service()
    await vad.initialize()
    vad.reset()
    
    # Generate test chunk (20ms)
    chunk = generate_speech_audio(20)
    
    # Measure latency over 100 iterations
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        vad.process_chunk(chunk)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    passed = avg_latency < 5
    log_result("T5.3", passed, f"avg={avg_latency:.2f}ms, max={max_latency:.2f}ms", avg_latency)


# ===========================================
# ASR Tests
# ===========================================

async def test_t5_4_asr_arabic():
    """T5.4: ASR - Arabic Transcription"""
    print("\n" + "="*50)
    print("T5.4: ASR - Arabic Transcription")
    print("="*50)
    
    asr = get_asr_service()
    await asr.initialize()
    
    # Generate mock audio (real test needs actual Arabic audio)
    audio = generate_speech_audio(3000)
    
    start = time.perf_counter()
    try:
        result = await asr.transcribe(audio, language="ar")
        latency = (time.perf_counter() - start) * 1000
        
        # Check if we got text back
        has_text = len(result.text) > 0
        log_result("T5.4", has_text, f"Text: {result.text[:50]}...", latency)
        
    except Exception as e:
        log_result("T5.4", False, f"Error: {e}")


async def test_t5_6_asr_latency():
    """T5.6: ASR - Latency (<300ms)"""
    print("\n" + "="*50)
    print("T5.6: ASR - Latency (<300ms)")
    print("="*50)
    
    asr = get_asr_service()
    await asr.initialize()
    
    # 3 seconds of audio
    audio = generate_speech_audio(3000)
    
    start = time.perf_counter()
    try:
        await asr.transcribe(audio, language="ar")
        latency = (time.perf_counter() - start) * 1000
        
        passed = latency < 300
        log_result("T5.6", passed, f"Latency: {latency:.0f}ms", latency)
        
    except Exception as e:
        log_result("T5.6", False, f"Error: {e}")


# ===========================================
# LLM Tests
# ===========================================

async def test_t5_7_llm_response_format():
    """T5.7: LLM - Response Format (JSON)"""
    print("\n" + "="*50)
    print("T5.7: LLM - Response Format")
    print("="*50)
    
    llm = get_llm_service()
    await llm.initialize()
    
    start = time.perf_counter()
    try:
        segments = await llm.generate_response(
            user_message="مرحبا، أبغى أحجز موعد",
            conversation_history=[],
        )
        latency = (time.perf_counter() - start) * 1000
        
        # Check response format
        has_segments = len(segments) > 0
        has_speaker = all(hasattr(s, 'speaker') for s in segments)
        has_text = all(hasattr(s, 'text') for s in segments)
        
        passed = has_segments and has_speaker and has_text
        log_result("T5.7", passed, f"{len(segments)} segments, valid format", latency)
        
    except Exception as e:
        log_result("T5.7", False, f"Error: {e}")


async def test_t5_8_llm_dual_persona():
    """T5.8: LLM - Dual Persona"""
    print("\n" + "="*50)
    print("T5.8: LLM - Dual Persona")
    print("="*50)
    
    llm = get_llm_service()
    await llm.initialize()
    
    try:
        segments = await llm.generate_response(
            user_message="أبغى أستشير دكتور عن حالتي الصحية",
            conversation_history=[],
        )
        
        speakers = [s.speaker for s in segments]
        has_sara = "sara" in speakers
        
        log_result("T5.8", has_sara, f"Speakers: {speakers}")
        
    except Exception as e:
        log_result("T5.8", False, f"Error: {e}")


async def test_t5_11_llm_ttft():
    """T5.11: LLM - TTFT (<200ms)"""
    print("\n" + "="*50)
    print("T5.11: LLM - TTFT (<200ms)")
    print("="*50)
    
    llm = get_llm_service()
    await llm.initialize()
    
    start = time.perf_counter()
    first_token_time = None
    
    try:
        async for _ in llm.generate_stream(
            user_message="مرحبا",
            conversation_history=[],
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()
            break
        
        if first_token_time:
            ttft = (first_token_time - start) * 1000
            passed = ttft < 200
            log_result("T5.11", passed, f"TTFT: {ttft:.0f}ms", ttft)
        else:
            log_result("T5.11", False, "No tokens received")
            
    except Exception as e:
        log_result("T5.11", False, f"Error: {e}")


# ===========================================
# TTS Tests
# ===========================================

async def test_t5_12_tts_sara():
    """T5.12: TTS - Sara Voice"""
    print("\n" + "="*50)
    print("T5.12: TTS - Sara Voice")
    print("="*50)
    
    tts = get_tts_service()
    await tts.initialize()
    
    start = time.perf_counter()
    try:
        audio = await tts.synthesize(
            text="مرحباً! كيف أقدر أساعدك اليوم؟",
            voice=Voice.SARA,
        )
        latency = (time.perf_counter() - start) * 1000
        
        has_audio = len(audio) > 0
        log_result("T5.12", has_audio, f"{len(audio)} bytes", latency)
        
    except Exception as e:
        log_result("T5.12", False, f"Error: {e}")


async def test_t5_13_tts_nexus():
    """T5.13: TTS - Nexus Voice"""
    print("\n" + "="*50)
    print("T5.13: TTS - Nexus Voice")
    print("="*50)
    
    tts = get_tts_service()
    await tts.initialize()
    
    start = time.perf_counter()
    try:
        audio = await tts.synthesize(
            text="أهلاً بك في عيادة نكسوس مراكل الطبية",
            voice=Voice.NEXUS,
        )
        latency = (time.perf_counter() - start) * 1000
        
        has_audio = len(audio) > 0
        log_result("T5.13", has_audio, f"{len(audio)} bytes", latency)
        
    except Exception as e:
        log_result("T5.13", False, f"Error: {e}")


async def test_t5_14_tts_ttfb():
    """T5.14: TTS - TTFB (<100ms)"""
    print("\n" + "="*50)
    print("T5.14: TTS - TTFB (<100ms)")
    print("="*50)
    
    tts = get_tts_service()
    await tts.initialize()
    
    start = time.perf_counter()
    first_byte_time = None
    
    try:
        async for chunk in tts.synthesize_stream(
            text="مرحبا",
            voice=Voice.SARA,
        ):
            if first_byte_time is None:
                first_byte_time = time.perf_counter()
            break
        
        if first_byte_time:
            ttfb = (first_byte_time - start) * 1000
            passed = ttfb < 100
            log_result("T5.14", passed, f"TTFB: {ttfb:.0f}ms", ttfb)
        else:
            log_result("T5.14", False, "No audio received")
            
    except Exception as e:
        log_result("T5.14", False, f"Error: {e}")


# ===========================================
# Full Pipeline Test
# ===========================================

async def test_t5_15_e2e_latency():
    """T5.15: End-to-End Latency (<800ms)"""
    print("\n" + "="*50)
    print("T5.15: End-to-End Latency (<800ms)")
    print("="*50)
    
    pipeline = get_pipeline_service()
    await pipeline.initialize()
    
    # Create test session
    session = pipeline.create_session("test-e2e-001")
    
    # Generate test audio
    audio_buffer = generate_speech_audio(2000)
    
    # Mock output callback
    async def mock_output(chunk: bytes):
        pass
    
    start = time.perf_counter()
    try:
        metrics = await pipeline.process_turn(
            session=session,
            audio_buffer=audio_buffer,
            output_callback=mock_output,
        )
        
        total_ms = metrics.get("total_ms", 0)
        passed = total_ms < 800
        
        detail = (
            f"ASR={metrics.get('asr_ms', 0):.0f}ms, "
            f"LLM={metrics.get('llm_ms', 0):.0f}ms, "
            f"TTS={metrics.get('tts_ms', 0):.0f}ms"
        )
        log_result("T5.15", passed, detail, total_ms)
        
    except Exception as e:
        log_result("T5.15", False, f"Error: {e}")
    finally:
        pipeline.end_session("test-e2e-001")


# ===========================================
# Main
# ===========================================

async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  PHASE 5: AI PIPELINE TESTS")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)
    
    # VAD Tests
    await test_t5_1_vad_speech_detection()
    await test_t5_2_vad_silence_detection()
    await test_t5_3_vad_latency()
    
    # ASR Tests
    await test_t5_4_asr_arabic()
    await test_t5_6_asr_latency()
    
    # LLM Tests
    await test_t5_7_llm_response_format()
    await test_t5_8_llm_dual_persona()
    await test_t5_11_llm_ttft()
    
    # TTS Tests
    await test_t5_12_tts_sara()
    await test_t5_13_tts_nexus()
    await test_t5_14_tts_ttfb()
    
    # Full Pipeline
    await test_t5_15_e2e_latency()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        latency = f" [{r['latency_ms']:.0f}ms]" if r["latency_ms"] > 0 else ""
        print(f"  {status} {r['test']}{latency}")
    
    print("-"*60)
    print(f"  Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️  Some tests failed")
    
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
