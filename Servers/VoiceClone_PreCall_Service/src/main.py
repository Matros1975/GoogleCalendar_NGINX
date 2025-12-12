"""
Main entry point for VoiceClone Pre-Call Service.

FastAPI application with async endpoints for 3CX and ElevenLabs webhooks.
"""

import os
import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.auth.hmac_validator import HMACValidator
from src.handlers import twilio_handler
from src.handlers.postcall_handler import PostCallHandler
from src.services.database_service import DatabaseService
from src.services.elevenlabs_client import ElevenLabsService
from src.services.storage_service import StorageService
from src.services.voice_clone_service import VoiceCloneService
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.services.call_controller import CallController
from src.services.audio_service import AudioService
from src.models.webhook_models import (
    PostCallWebhookPayload,
    HealthCheckResponse,
    CacheInvalidationRequest,
    CacheInvalidationResponse,
    StatisticsResponse,
)
from src.utils.logger import setup_logger, get_logger

# Setup logging
logger = setup_logger()

# Global service instances
db_service: DatabaseService = None
elevenlabs_service: ElevenLabsService = None
storage_service: StorageService = None
voice_clone_service: VoiceCloneService = None
async_service: VoiceCloneAsyncService = None
call_controller: CallController = None
audio_service: AudioService = None
sip_server = None
postcall_handler: PostCallHandler = None
hmac_validator: HMACValidator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global db_service, elevenlabs_service, storage_service
    global voice_clone_service, async_service, call_controller, audio_service
    global postcall_handler, hmac_validator, sip_server
    
    # Startup
    logger.info("Starting VoiceClone Pre-Call Service...")
    
    settings = get_settings()
    
    # Initialize services
    db_service = DatabaseService()
    await db_service.init()
    
    elevenlabs_service = ElevenLabsService()
    storage_service = StorageService()
    audio_service = AudioService()
    
    voice_clone_service = VoiceCloneService(
        db_service=db_service,
        elevenlabs_service=elevenlabs_service,
        storage_service=storage_service,
    )
    
    async_service = VoiceCloneAsyncService(
        voice_clone_service=voice_clone_service,
        elevenlabs_service=elevenlabs_service,
        db_service=db_service,
    )
    
    # Initialize call controller
    call_controller = CallController(
        voice_clone_service=async_service,
        database_service=db_service,
    )
    
    # Initialize handlers
    twilio_handler.init_handler(call_controller)
    postcall_handler = PostCallHandler(db_service=db_service)
    
    # Initialize HMAC validator for ElevenLabs webhooks
    hmac_validator = HMACValidator(secret=settings.webhook_secret)
    
    # Initialize SIP server (if enabled)
    if settings.enable_sip_handler:
        try:
            from src.handlers.sip_handler import SIPServer
            logger.info("SIP handler enabled - starting SIP server...")
            sip_server = SIPServer(
                call_controller=call_controller,
                audio_service=audio_service,
                host=settings.sip_host,
                port=settings.sip_port
            )
            await sip_server.start()
            logger.info(f"✅ SIP server started on {settings.sip_host}:{settings.sip_port}")
        except ImportError as e:
            logger.warning(f"⚠️  SIP handler enabled but dependencies not available: {e}")
            logger.warning("   Install PJSUA2 to enable SIP support")
        except Exception as e:
            logger.error(f"❌ Failed to start SIP server: {e}")
            raise
    else:
        logger.info("SIP handler disabled (set ENABLE_SIP_HANDLER=true to enable)")
    
    logger.info("VoiceClone Pre-Call Service started successfully")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    logger.info(f"Storage: {settings.voice_sample_storage}")
    logger.info(f"Cache TTL: {settings.cache_ttl}s")
    
    yield
    
    # Shutdown
    logger.info("VoiceClone Pre-Call Service shutting down...")
    
    if sip_server:
        try:
            await sip_server.stop()
        except Exception as e:
            logger.error(f"Error stopping SIP server: {e}")
    
    if audio_service:
        try:
            await audio_service.close()
        except Exception as e:
            logger.error(f"Error closing audio service: {e}")
    
    if db_service:
        await db_service.close()


# Initialize FastAPI app
app = FastAPI(
    title="VoiceClone Pre-Call Service",
    version="2.0.0",
    description="Twilio → ElevenLabs voice cloning integration with async TwiML workflow",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# CORS middleware
cors_origins = settings.get_cors_origins_list()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Include routers
app.include_router(twilio_handler.router)


@app.get("/health")
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for Docker/NGINX monitoring.
    
    Returns:
        HealthCheckResponse with service status
    """
    try:
        # Check database
        db_status = "ok" if await db_service.health_check() else "error"
        
        # Check ElevenLabs API
        elevenlabs_status = "ok" if await elevenlabs_service.health_check() else "error"
        
        # Overall status
        if db_status == "ok" and elevenlabs_status == "ok":
            overall_status = "ok"
        elif db_status == "error" or elevenlabs_status == "error":
            overall_status = "degraded" if (db_status == "ok" or elevenlabs_status == "ok") else "error"
        else:
            overall_status = "ok"
        
        return HealthCheckResponse(
            status=overall_status,
            database=db_status,
            elevenlabs=elevenlabs_status,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="error",
            database="error",
            elevenlabs="error",
            timestamp=datetime.utcnow()
        )


@app.post("/webhook/elevenlabs/postcall")
async def elevenlabs_postcall_webhook(
    request: Request,
    elevenlabs_signature: str = Header(None, alias="elevenlabs-signature")
):
    """
    ElevenLabs POST-call webhook endpoint.
    
    Handles post-call events from ElevenLabs Voice Agent.
    
    Returns:
        200 OK for successful processing
        400 Bad Request for invalid payloads
        401 Unauthorized for invalid signatures
        500 Internal Server Error for processing failures
    """
    try:
        # Read request body
        body = await request.body()
        
        # Validate HMAC signature
        webhook_secret = settings.webhook_secret
        validator = HMACValidator(secret=webhook_secret)
        is_valid, error_message = validator.validate(elevenlabs_signature, body)
        
        if not is_valid:
            logger.warning(f"ElevenLabs HMAC validation failed: {error_message}")
            if "expired" in error_message.lower():
                raise HTTPException(status_code=400, detail=error_message)
            raise HTTPException(status_code=401, detail=error_message)
        
        # Parse JSON payload
        try:
            payload_dict = json.loads(body.decode("utf-8"))
            payload = PostCallWebhookPayload(**payload_dict)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        except Exception as e:
            logger.error(f"Invalid payload format: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        
        # Handle POST-call event
        result = await postcall_handler.handle(payload)
        return JSONResponse(content=result, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"ElevenLabs webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/api/v1/cache/{caller_id}")
async def invalidate_cache(caller_id: str) -> CacheInvalidationResponse:
    """
    Invalidate voice clone cache for a specific caller.
    
    Args:
        caller_id: Caller phone number
        
    Returns:
        CacheInvalidationResponse with result
    """
    try:
        success = await voice_clone_service.invalidate_clone_cache(caller_id)
        
        if success:
            message = f"Cache invalidated for caller {caller_id}"
        else:
            message = f"No cache entry found for caller {caller_id}"
        
        return CacheInvalidationResponse(success=success, message=message)
        
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/statistics")
async def get_statistics() -> StatisticsResponse:
    """
    Get voice clone statistics.
    
    Returns:
        StatisticsResponse with metrics
    """
    try:
        stats = await voice_clone_service.get_clone_statistics()
        return StatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point for running the service."""
    import uvicorn
    
    settings = get_settings()
    host = settings.host
    port = settings.port
    log_level = settings.log_level.lower()
    
    logger.info(f"Starting VoiceClone Pre-Call Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False
    )


if __name__ == "__main__":
    main()
