"""
Nexus Miracle - Health Router

Health check endpoint for monitoring and load balancer probes.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    version: str
    environment: str
    timestamp: str
    services: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the application and its services.",
)
async def health_check() -> dict[str, Any]:
    """
    Check application health status.
    
    Returns:
        Health status including version, environment, and service states.
    """
    settings = get_settings()
    
    # TODO: Add actual service health checks
    services = {
        "telnyx": "ok",  # Placeholder
        "elevenlabs": "ok",  # Placeholder
        "gemini": "ok",  # Placeholder
        "vad": "ok",  # Placeholder
    }
    
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Returns whether the application is ready to accept traffic.",
)
async def readiness_check() -> dict[str, str]:
    """
    Check if application is ready to serve requests.
    
    Used by Kubernetes/load balancers to determine if traffic
    should be routed to this instance.
    
    Returns:
        Readiness status.
    """
    # TODO: Add actual readiness checks (DB connections, API keys valid, etc.)
    return {"status": "ready"}


@router.get(
    "/live",
    summary="Liveness Check",
    description="Returns whether the application is alive.",
)
async def liveness_check() -> dict[str, str]:
    """
    Check if application is alive and responsive.
    
    Used by Kubernetes to determine if the container should be restarted.
    
    Returns:
        Liveness status.
    """
    return {"status": "alive"}
