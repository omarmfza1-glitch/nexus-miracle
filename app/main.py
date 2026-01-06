"""
Nexus Miracle - FastAPI Application

Main application entry point with middleware, exception handlers,
lifespan events, and router mounting.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import get_settings
from app.exceptions import NexusMiracleException
from app.routers import admin, appointments, doctors, health, insurance, patients, telephony

# ===========================================
# Logging Configuration
# ===========================================

def setup_logging() -> None:
    """Configure loguru logging for console and file output."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with color
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )
    
    # File handler with rotation
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "nexus_miracle_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="00:00",  # New file at midnight
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=settings.debug,
    )
    
    logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"env={settings.app_env}"
    )


# ===========================================
# Lifespan Events
# ===========================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.
    
    Startup:
        - Configure logging
        - Initialize services
        - Warm up connections
    
    Shutdown:
        - Close connections
        - Cleanup resources
    """
    settings = get_settings()
    
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    from app.services.db_service import init_db, create_tables
    await init_db()
    await create_tables()
    logger.info("Database initialized")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Close database connections
    from app.services.db_service import close_db
    await close_db()
    
    logger.info("Application shutdown complete")


# ===========================================
# Application Factory
# ===========================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-powered medical contact center for Saudi Arabia. "
            "Handles phone calls with real-time ASR, LLM, and TTS processing."
        ),
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    
    # ===========================================
    # Middleware
    # ===========================================
    
    # CORS middleware (allow all for development)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ===========================================
    # Exception Handlers
    # ===========================================
    
    @app.exception_handler(NexusMiracleException)
    async def nexus_exception_handler(
        request: Request,
        exc: NexusMiracleException,
    ) -> ORJSONResponse:
        """Handle application-specific exceptions."""
        logger.error(f"NexusMiracleException: {exc.message}", extra=exc.details)
        return ORJSONResponse(
            status_code=500,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> ORJSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(f"Unhandled exception: {exc}")
        return ORJSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {"type": exc.__class__.__name__} if settings.debug else {},
            },
        )
    
    # ===========================================
    # Routers
    # ===========================================
    
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(telephony.router, prefix="/api/telephony", tags=["Telephony"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    app.include_router(doctors.router, prefix="/api/doctors", tags=["Doctors"])
    app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
    app.include_router(insurance.router, prefix="/api/insurance", tags=["Insurance"])
    app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
    
    # ===========================================
    # Static Files
    # ===========================================
    
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    return app


# Create the application instance
app = create_app()
