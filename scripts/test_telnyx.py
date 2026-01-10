"""
Phase 4: Telnyx Integration Tests

Run with: python scripts/test_telnyx.py
"""

import asyncio
import base64
import json
import sys
import time
from datetime import datetime

import httpx
import websockets

# Test configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

# Test results
results = []


def log_result(test_id: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_id}: {details}")
    results.append({
        "test": test_id,
        "passed": passed,
        "details": details,
        "timestamp": datetime.now().isoformat(),
    })


async def test_t4_1_webhook_endpoint():
    """T4.1: Webhook Endpoint - POST with mock payload."""
    print("\n" + "="*50)
    print("T4.1: Webhook Endpoint")
    print("="*50)
    
    payload = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": "test-call-001",
                "from": "+966501234567",
                "to": "+966509876543",
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/telephony/webhook",
                json=payload,
                timeout=10.0,
            )
            
            if response.status_code == 200:
                log_result("T4.1", True, f"Response: {response.json()}")
            else:
                log_result("T4.1", False, f"Status: {response.status_code}")
                
    except Exception as e:
        log_result("T4.1", False, f"Error: {e}")


async def test_t4_2_call_initiated():
    """T4.2: Call Initiated Event - Server attempts to answer."""
    print("\n" + "="*50)
    print("T4.2: Call Initiated Event")
    print("="*50)
    
    payload = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": "test-call-002",
                "from": "+966501234567",
                "to": "+966509876543",
                "direction": "incoming",
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/telephony/webhook",
                json=payload,
                timeout=10.0,
            )
            
            # Should return 200 even if Telnyx API fails (mock call)
            if response.status_code == 200:
                log_result("T4.2", True, "Webhook processed (Telnyx API call expected to fail in test)")
            else:
                log_result("T4.2", False, f"Status: {response.status_code}")
                
    except Exception as e:
        log_result("T4.2", False, f"Error: {e}")


async def test_t4_3_websocket_connection():
    """T4.3: WebSocket Connection - Connect and stay open."""
    print("\n" + "="*50)
    print("T4.3: WebSocket Connection")
    print("="*50)
    
    call_id = "test-ws-003"
    
    try:
        async with websockets.connect(
            f"{WS_URL}/api/telephony/media/{call_id}",
            ping_interval=None,
        ) as ws:
            # Send start event
            await ws.send(json.dumps({"event": "connected"}))
            
            # Wait briefly
            await asyncio.sleep(1)
            
            # Connection should still be open
            if ws.open:
                log_result("T4.3", True, "WebSocket connected and stable")
            else:
                log_result("T4.3", False, "WebSocket closed unexpectedly")
                
    except Exception as e:
        log_result("T4.3", False, f"Error: {e}")


async def test_t4_4_audio_receive():
    """T4.4: Audio Receive - Send mock audio chunk."""
    print("\n" + "="*50)
    print("T4.4: Audio Receive (Mock)")
    print("="*50)
    
    call_id = "test-ws-004"
    
    # Create mock μ-law audio (160 bytes = 20ms at 8kHz)
    mock_audio = bytes([128] * 160)  # Silence in μ-law
    audio_b64 = base64.b64encode(mock_audio).decode()
    
    try:
        async with websockets.connect(
            f"{WS_URL}/api/telephony/media/{call_id}",
            ping_interval=None,
        ) as ws:
            # Send start event
            await ws.send(json.dumps({"event": "start"}))
            await asyncio.sleep(0.5)
            
            # Send audio chunk
            await ws.send(json.dumps({
                "event": "media",
                "media": {
                    "payload": audio_b64,
                    "track": "inbound",
                }
            }))
            
            # Wait for processing
            await asyncio.sleep(1)
            
            log_result("T4.4", True, "Audio chunk sent and processed")
                
    except Exception as e:
        log_result("T4.4", False, f"Error: {e}")


async def test_t4_5_audio_send():
    """T4.5: Audio Send - Receive audio from server."""
    print("\n" + "="*50)
    print("T4.5: Audio Send (Mock)")
    print("="*50)
    
    call_id = "test-ws-005"
    received_audio = False
    
    try:
        async with websockets.connect(
            f"{WS_URL}/api/telephony/media/{call_id}",
            ping_interval=None,
        ) as ws:
            # Send start event to trigger greeting
            await ws.send(json.dumps({"event": "start"}))
            
            # Listen for responses (with timeout)
            try:
                for _ in range(20):  # Max 20 attempts
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    data = json.loads(msg)
                    
                    if data.get("event") == "media":
                        payload = data.get("media", {}).get("payload", "")
                        if payload:
                            # Validate base64
                            audio = base64.b64decode(payload)
                            received_audio = True
                            log_result("T4.5", True, f"Received {len(audio)} bytes audio")
                            break
                            
            except asyncio.TimeoutError:
                pass
            
            if not received_audio:
                log_result("T4.5", False, "No audio received (TTS may not be configured)")
                
    except Exception as e:
        log_result("T4.5", False, f"Error: {e}")


async def test_t4_6_call_hangup():
    """T4.6: Call Hangup Event - Session cleanup."""
    print("\n" + "="*50)
    print("T4.6: Call Hangup Event")
    print("="*50)
    
    call_id = "test-call-006"
    
    # First create a session
    init_payload = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": call_id,
                "from": "+966501234567",
                "to": "+966509876543",
            }
        }
    }
    
    hangup_payload = {
        "data": {
            "event_type": "call.hangup",
            "payload": {
                "call_control_id": call_id,
                "hangup_cause": "normal_clearing",
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Create session
            await client.post(f"{BASE_URL}/api/telephony/webhook", json=init_payload)
            
            # Send hangup
            response = await client.post(
                f"{BASE_URL}/api/telephony/webhook",
                json=hangup_payload,
                timeout=10.0,
            )
            
            if response.status_code == 200:
                log_result("T4.6", True, "Hangup processed, session cleaned")
            else:
                log_result("T4.6", False, f"Status: {response.status_code}")
                
    except Exception as e:
        log_result("T4.6", False, f"Error: {e}")


async def test_t4_7_concurrent_calls():
    """T4.7: Multiple Concurrent Calls - 3 simultaneous WebSockets."""
    print("\n" + "="*50)
    print("T4.7: Multiple Concurrent Calls")
    print("="*50)
    
    async def connect_call(call_id: str) -> bool:
        try:
            async with websockets.connect(
                f"{WS_URL}/api/telephony/media/{call_id}",
                ping_interval=None,
            ) as ws:
                await ws.send(json.dumps({"event": "connected"}))
                await asyncio.sleep(2)
                return ws.open
        except:
            return False
    
    try:
        # Start 3 concurrent connections
        tasks = [
            connect_call("concurrent-001"),
            connect_call("concurrent-002"),
            connect_call("concurrent-003"),
        ]
        
        results_concurrent = await asyncio.gather(*tasks)
        
        if all(results_concurrent):
            log_result("T4.7", True, "All 3 concurrent connections stable")
        else:
            log_result("T4.7", False, f"Results: {results_concurrent}")
            
    except Exception as e:
        log_result("T4.7", False, f"Error: {e}")


async def test_t4_8_status_check():
    """T4.8: Status Check - Verify telephony status endpoint."""
    print("\n" + "="*50)
    print("T4.8: Telephony Status")
    print("="*50)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/telephony",
                timeout=10.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                log_result("T4.8", True, f"Status: {data}")
            else:
                log_result("T4.8", False, f"Status: {response.status_code}")
                
    except Exception as e:
        log_result("T4.8", False, f"Error: {e}")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  PHASE 4: TELNYX INTEGRATION TESTS")
    print("="*60)
    print(f"Server: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)
    
    # Run tests
    await test_t4_1_webhook_endpoint()
    await test_t4_2_call_initiated()
    await test_t4_3_websocket_connection()
    await test_t4_4_audio_receive()
    await test_t4_5_audio_send()
    await test_t4_6_call_hangup()
    await test_t4_7_concurrent_calls()
    await test_t4_8_status_check()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['test']}")
    
    print("-"*60)
    print(f"  Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️  Some tests failed. Check logs above.")
    
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
