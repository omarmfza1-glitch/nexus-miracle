"""
Integration Test Scenarios for Nexus Miracle.
These tests require a running backend and Telnyx connection.
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"


class IntegrationTests:
    """Integration test scenarios for manual/semi-automated testing."""
    
    def __init__(self):
        self.session = None
        self.results: list[tuple[str, bool, str]] = []
    
    async def setup(self):
        """Setup test session."""
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        """Cleanup test session."""
        if self.session:
            await self.session.close()
    
    async def test_t8_1_phone_booking_to_db(self):
        """
        T8.1: Phone Booking → DB
        
        Prerequisites:
        - Backend running
        - Telnyx configured
        
        Steps:
        1. Call Telnyx number
        2. Say: "أبغى أحجز موعد عند دكتور العظام يوم الثلاثاء"
        3. Complete booking flow
        
        Validation:
        - Check database for new appointment
        """
        print("\n📞 T8.1: Phone Booking → DB")
        print("   This test requires manual phone call")
        print("   After calling, check: GET /api/appointments")
        
        try:
            async with self.session.get(f"{BASE_URL}/api/appointments") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Current appointments: {len(data)}")
                    print("   ⏳ Make phone call, then verify new appointment appears")
                    return True, "Manual verification required"
                else:
                    return False, f"API error: {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_t8_3_web_booking_to_call(self):
        """
        T8.3: Web Booking → Call Info
        
        Steps:
        1. Create booking via web API
        2. Call and ask about existing booking
        
        Validation:
        - LLM should recognize patient and booking
        """
        print("\n🌐 T8.3: Web Booking → Call Info")
        
        # Check existing appointments instead of creating
        try:
            async with self.session.get(f"{BASE_URL}/api/appointments") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Current appointments: {len(data)}")
                    print("   🌐 Book via http://localhost:3001/book")
                    print("   📞 Then call and verify LLM knows about booking")
                    return True, "Use web UI to book, then call"
                else:
                    return False, f"Failed to get appointments: {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_t8_4_settings_to_live_call(self):
        """
        T8.4: Settings → Live Call
        
        Steps:
        1. Change system prompt via admin
        2. Make call
        3. Verify new prompt is used
        """
        print("\n⚙️ T8.4: Settings → Live Call")
        
        # Get current prompt
        try:
            async with self.session.get(f"{BASE_URL}/api/admin/settings") as resp:
                if resp.status == 200:
                    settings = await resp.json()
                    print(f"   Environment: {settings.get('environment', 'N/A')}")
                    print("   📝 Modify prompt in admin, then call to verify")
                    return True, "Check admin settings then call"
                else:
                    return False, f"Failed to get settings: {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_t8_5_voice_settings_to_tts(self):
        """
        T8.5: Voice Settings → TTS
        
        Steps:
        1. Change voice settings (stability, style)
        2. Make call
        3. Verify voice sounds different
        """
        print("\n🎤 T8.5: Voice Settings → TTS")
        
        try:
            async with self.session.get(f"{BASE_URL}/api/admin/voices") as resp:
                if resp.status == 200:
                    voice = await resp.json()
                    sara = voice.get('sara', {})
                    print(f"   Sara stability: {sara.get('stability', 'N/A')}")
                    print(f"   Sara similarity: {sara.get('similarity_boost', 'N/A')}")
                    print("   🎚️ Adjust settings, then call to verify")
                    return True, "Adjust voice settings then call"
                else:
                    return False, f"Failed to get voice: {resp.status}"
        except Exception as e:
            return False, str(e)
    
    async def test_t8_6_error_recovery_asr(self):
        """
        T8.6: Error Recovery - ASR Fail
        
        Validation:
        - Circuit breaker should activate
        - Fallback message should play
        """
        print("\n⚡ T8.6: Error Recovery - ASR Fail")
        
        try:
            # Check circuit breaker stats
            async with self.session.get(f"{BASE_URL}/api/health") as resp:
                if resp.status == 200:
                    print("   Backend is healthy")
                    print("   🔧 To test: temporarily disable ElevenLabs key")
                    print("   Expected: 'ما سمعتك زين. ممكن تعيد؟'")
                    return True, "Manual test required"
                else:
                    return False, "Backend not healthy"
        except Exception as e:
            return False, str(e)
    
    async def test_t8_7_error_recovery_llm(self):
        """
        T8.7: Error Recovery - LLM Fail
        
        Validation:
        - Circuit breaker should activate
        - Fallback message should play
        """
        print("\n⚡ T8.7: Error Recovery - LLM Fail")
        print("   🔧 To test: temporarily disable Google API key")
        print("   Expected: 'النظام مشغول، لحظة وأرجع لك'")
        return True, "Manual test required"
    
    async def test_t8_8_barge_in(self):
        """
        T8.8: Barge-in Test
        
        Steps:
        1. Call and let AI respond
        2. Interrupt mid-sentence
        3. Verify AI stops immediately
        """
        print("\n🎯 T8.8: Barge-in")
        print("   📞 Call and interrupt AI while speaking")
        print("   Expected: AI stops within 50ms")
        return True, "Manual test required"
    
    async def run_all(self):
        """Run all integration tests."""
        print("=" * 60)
        print("🧪 Nexus Miracle Integration Tests")
        print("=" * 60)
        print(f"Backend: {BASE_URL}")
        print(f"Frontend: {FRONTEND_URL}")
        
        await self.setup()
        
        tests = [
            ("T8.1", self.test_t8_1_phone_booking_to_db),
            ("T8.3", self.test_t8_3_web_booking_to_call),
            ("T8.4", self.test_t8_4_settings_to_live_call),
            ("T8.5", self.test_t8_5_voice_settings_to_tts),
            ("T8.6", self.test_t8_6_error_recovery_asr),
            ("T8.7", self.test_t8_7_error_recovery_llm),
            ("T8.8", self.test_t8_8_barge_in),
        ]
        
        for name, test_fn in tests:
            try:
                result, message = await test_fn()
                self.results.append((name, result, message))
            except Exception as e:
                self.results.append((name, False, str(e)))
        
        await self.teardown()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Integration Test Summary")
        print("=" * 60)
        
        for name, passed, message in self.results:
            status = "✅" if passed else "❌"
            print(f"   {status} {name}: {message}")
        
        print("\n   ℹ️ Most tests require manual phone verification")


async def main():
    tester = IntegrationTests()
    await tester.run_all()


if __name__ == "__main__":
    asyncio.run(main())
