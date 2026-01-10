"""
Load Testing Script for Nexus Miracle.
Tests: Concurrent API requests, response times, memory usage.
"""

import asyncio
import aiohttp
import time
import statistics
import psutil
import os
from dataclasses import dataclass
from typing import Any

# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
CONCURRENT_REQUESTS = 100
DURATION_SECONDS = 10


@dataclass
class LoadTestResult:
    """Results from a load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    requests_per_second: float
    error_rate: float
    memory_start_mb: float
    memory_end_mb: float


async def make_request(session: aiohttp.ClientSession, endpoint: str) -> tuple[bool, float]:
    """Make a single request and return success status and latency."""
    start = time.perf_counter()
    try:
        async with session.get(f"{BASE_URL}{endpoint}") as response:
            await response.text()
            latency_ms = (time.perf_counter() - start) * 1000
            return response.status == 200, latency_ms
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return False, latency_ms


async def run_load_test(
    endpoint: str,
    requests_per_second: int = 100,
    duration_seconds: int = 10,
) -> LoadTestResult:
    """Run load test against an endpoint."""
    print(f"\n🔥 Load Testing: {endpoint}")
    print(f"   Target: {requests_per_second} req/s for {duration_seconds}s")
    
    # Record starting memory
    process = psutil.Process()
    memory_start = process.memory_info().rss / 1024 / 1024
    
    successes = 0
    failures = 0
    latencies: list[float] = []
    
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        while time.perf_counter() < end_time:
            # Launch batch of concurrent requests
            tasks = [
                make_request(session, endpoint)
                for _ in range(requests_per_second)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failures += 1
                else:
                    success, latency = result
                    latencies.append(latency)
                    if success:
                        successes += 1
                    else:
                        failures += 1
            
            # Wait for next second
            await asyncio.sleep(max(0, 1 - (time.perf_counter() % 1)))
    
    # Record ending memory
    memory_end = process.memory_info().rss / 1024 / 1024
    
    # Calculate statistics
    total = successes + failures
    sorted_latencies = sorted(latencies) if latencies else [0]
    
    result = LoadTestResult(
        total_requests=total,
        successful_requests=successes,
        failed_requests=failures,
        avg_latency_ms=statistics.mean(latencies) if latencies else 0,
        p50_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.5)],
        p95_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.95)],
        p99_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.99)],
        requests_per_second=total / duration_seconds,
        error_rate=(failures / total * 100) if total > 0 else 0,
        memory_start_mb=memory_start,
        memory_end_mb=memory_end,
    )
    
    return result


def print_results(result: LoadTestResult, test_name: str) -> bool:
    """Print test results and return pass/fail."""
    print(f"\n📊 Results: {test_name}")
    print(f"   Total Requests: {result.total_requests}")
    print(f"   Successful: {result.successful_requests}")
    print(f"   Failed: {result.failed_requests}")
    print(f"   Error Rate: {result.error_rate:.2f}%")
    print(f"   Avg Latency: {result.avg_latency_ms:.2f}ms")
    print(f"   P50 Latency: {result.p50_latency_ms:.2f}ms")
    print(f"   P95 Latency: {result.p95_latency_ms:.2f}ms")
    print(f"   P99 Latency: {result.p99_latency_ms:.2f}ms")
    print(f"   RPS: {result.requests_per_second:.1f}")
    print(f"   Memory: {result.memory_start_mb:.1f}MB → {result.memory_end_mb:.1f}MB")
    
    # Check pass/fail criteria
    passed = True
    
    if result.avg_latency_ms > 100:
        print(f"   ❌ FAIL: Avg latency > 100ms")
        passed = False
    else:
        print(f"   ✅ PASS: Avg latency < 100ms")
    
    if result.error_rate > 1:
        print(f"   ❌ FAIL: Error rate > 1%")
        passed = False
    else:
        print(f"   ✅ PASS: Error rate < 1%")
    
    memory_diff = result.memory_end_mb - result.memory_start_mb
    if memory_diff > 100:
        print(f"   ⚠️ WARNING: Memory increased by {memory_diff:.1f}MB")
    
    return passed


async def test_health_endpoint():
    """T8.11: Test /api/health endpoint at 100 req/s."""
    result = await run_load_test(
        endpoint="/api/health",
        requests_per_second=100,
        duration_seconds=10,
    )
    return print_results(result, "T8.11: API Load - 100 req/s")


async def test_settings_endpoint():
    """Test /api/settings endpoint."""
    result = await run_load_test(
        endpoint="/api/settings",
        requests_per_second=50,
        duration_seconds=5,
    )
    return print_results(result, "Settings API Load")


async def test_doctors_endpoint():
    """Test /api/doctors endpoint."""
    result = await run_load_test(
        endpoint="/api/doctors",
        requests_per_second=50,
        duration_seconds=5,
    )
    return print_results(result, "Doctors API Load")


async def test_memory_stability():
    """T8.12: Test memory stability under load."""
    print("\n🧠 Testing Memory Stability...")
    
    process = psutil.Process()
    memory_samples: list[float] = []
    
    # Sample memory over time while making requests
    connector = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i in range(10):
            # Make batch of requests
            tasks = [make_request(session, "/health") for _ in range(50)]
            await asyncio.gather(*tasks)
            
            # Sample memory
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)
            print(f"   Sample {i+1}: {memory_mb:.1f}MB")
            
            await asyncio.sleep(1)
    
    # Check for memory leak
    memory_growth = memory_samples[-1] - memory_samples[0]
    max_memory = max(memory_samples)
    
    print(f"\n   Memory Growth: {memory_growth:.1f}MB")
    print(f"   Max Memory: {max_memory:.1f}MB")
    
    if max_memory < 2048:  # 2GB limit
        print(f"   ✅ PASS: Memory < 2GB")
        return True
    else:
        print(f"   ❌ FAIL: Memory >= 2GB")
        return False


async def main():
    """Run all load tests."""
    print("=" * 60)
    print("🚀 Nexus Miracle Load Testing Suite")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    
    results = []
    
    # T8.11: API Load Test
    try:
        results.append(("T8.11: API Load", await test_health_endpoint()))
    except Exception as e:
        print(f"❌ T8.11 Failed: {e}")
        results.append(("T8.11: API Load", False))
    
    # T8.12: Memory Test
    try:
        results.append(("T8.12: Memory", await test_memory_stability()))
    except Exception as e:
        print(f"❌ T8.12 Failed: {e}")
        results.append(("T8.12: Memory", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Load Test Summary")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n   Total: {passed}/{len(results)} passed")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
