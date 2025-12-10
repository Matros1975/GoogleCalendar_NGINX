"""
Main entry point for Voice Clone Pre-Call Service.

This service handles:
- Incoming call webhooks from 3CX PBX
- POST-call webhooks from ElevenLabs
- Async voice cloning with greeting workflow
"""

import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.auth.hmac_validator import HMACValidator
from src.handlers.threecx_handler import ThreeCXHandler
from src.handlers.postcall_handler import PostCallHandler
from src.services.database_service import DatabaseService
from src.services.cache_service import CacheService
from src.services.storage_service import StorageService
from src.services.elevenlabs_client import ElevenLabsClient
from src.services.voice_clone_service import VoiceCloneService
from src.services.voice_clone_async_service import VoiceCloneAsyncService
from src.models.webhook_models import (
    ThreeCXWebhookPayload,
    PostCallWebhookPayload,
    HealthCheckResponse
)
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger()

# Global service instances
database_service: DatabaseService = None
cache_service: CacheService = None
storage_service: StorageService = None
elevenlabs_client: ElevenLabsClient = None
voice_clone_service: VoiceCloneService = None
async_voice_service: VoiceCloneAsyncService = None
threecx_handler: ThreeCXHandler = None
postcall_handler: PostCallHandler = None
hmac_validator: HMACValidator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global database_service, cache_service, storage_service, elevenlabs_client
    global voice_clone_service, async_voice_service, threecx_handler, postcall_handler
    global hmac_validator
    
    try:
        # Load configuration
        settings = get_settings()
        
        logger.info("Initializing Voice Clone Pre-Call Service...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Port: {settings.port}")
        
        # Initialize database service
        database_service = DatabaseService()
        await database_service.init()
        logger.info("Database service initialized")
        
        # Initialize cache service
        cache_service = CacheService()
        await cache_service.connect()
        logger.info("Cache service initialized")
        
        # Initialize storage service
        storage_service = StorageService()
        logger.info("Storage service initialized")
        
        # Initialize ElevenLabs client
        elevenlabs_client = ElevenLabsClient()
        await elevenlabs_client.connect()
        logger.info("ElevenLabs client initialized")
        
        # Initialize voice clone service
        voice_clone_service = VoiceCloneService(
            database_service=database_service,
            cache_service=cache_service,
            storage_service=storage_service,
            elevenlabs_client=elevenlabs_client
        )
        logger.info("Voice clone service initialized")
        
        # Initialize async voice clone service
        async_voice_service = VoiceCloneAsyncService(
            database_service=database_service,
            voice_clone_service=voice_clone_service,
            elevenlabs_client=elevenlabs_client
        )
        logger.info("Async voice clone service initialized")
        
        # Initialize handlers
        threecx_handler = ThreeCXHandler(async_service=async_voice_service)
        postcall_handler = PostCallHandler(database_service=database_service)
        logger.info("Handlers initialized")
        
        # Initialize HMAC validator
        hmac_validator = HMACValidator(secret=settings.webhook_secret)
        logger.info("HMAC validator initialized")
        
        logger.info("Voice Clone Pre-Call Service started successfully")
        
        yield
        
        # Shutdown
        logger.info("Shutting down Voice Clone Pre-Call Service...")
        
        if elevenlabs_client:
            await elevenlabs_client.disconnect()
        
        if cache_service:
            await cache_service.disconnect()
        
        if database_service:
            await database_service.close()
        
        logger.info("Voice Clone Pre-Call Service shut down successfully")
        
    except Exception as e:
        logger.exception(f"Error during application lifecycle: {e}")
        raise


# Initialize FastAPI app with lifespan handler
app = FastAPI(
    title="Voice Clone Pre-Call Service",
    version="1.0.0",
    description="Microservice for 3CX + ElevenLabs voice cloning integration",
    lifespan=lifespan
)

# Add CORS middleware
settings = get_settings()
cors_origins = settings.get_cors_origins_list()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Docker/NGINX monitoring.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - ElevenLabs API connectivity
    
    Returns:
        HealthCheckResponse with service status
    """
    try:
        # Check database
        db_status = "ok" if await database_service.health_check() else "error"
        
        # Check Redis
        redis_status = "ok" if await cache_service.health_check() else "error"
        
        # Check ElevenLabs API
        elevenlabs_status = "ok" if await elevenlabs_client.health_check() else "error"
        
        # Overall status
        if db_status == "ok" and redis_status == "ok" and elevenlabs_status == "ok":
            overall_status = "ok"
        elif db_status == "error" or redis_status == "error":
            overall_status = "error"
        else:
            overall_status = "degraded"
        
        return HealthCheckResponse(
            status=overall_status,
            database=db_status,
            redis=redis_status,
            elevenlabs=elevenlabs_status,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.exception(f"Health check error: {e}")
        return HealthCheckResponse(
            status="error",
            database="error",
            redis="error",
            elevenlabs="error",
            timestamp=datetime.utcnow()
        )


@app.post("/webhook/3cx")
async def threecx_webhook_endpoint(
    request: Request,
    x_signature: str = Header(None, alias="X-Signature")
):
    """
    3CX webhook endpoint for incoming call notifications.
    
    Handles:
    - IncomingCall: Triggers async voice cloning workflow
    - CallStateChanged: Logs call state changes
    - CallEnded: Logs call completion
    
    Security:
    - HMAC signature validation via X-Signature header
    
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
        if settings.threecx_webhook_secret:
            is_valid, error_message = hmac_validator.validate(x_signature, body)
            if not is_valid:
                logger.warning(f"3CX webhook HMAC validation failed: {error_message}")
                if "expired" in error_message.lower():
                    raise HTTPException(status_code=400, detail=error_message)
                raise HTTPException(status_code=401, detail=error_message)
        
        # Parse JSON payload
        import json
        try:
            payload_dict = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate with Pydantic model
        payload = ThreeCXWebhookPayload(**payload_dict)
        
        # Route to appropriate handler based on event type
        if payload.event_type == "IncomingCall":
            result = await threecx_handler.handle(payload)
            return JSONResponse(content=result.model_dump(), status_code=200)
        
        elif payload.event_type == "CallStateChanged":
            result = await threecx_handler.handle_call_state_changed(payload)
            return JSONResponse(content=result, status_code=200)
        
        elif payload.event_type == "CallEnded":
            result = await threecx_handler.handle_call_ended(payload)
            return JSONResponse(content=result, status_code=200)
        
        else:
            logger.error(f"Unknown event type: {payload.event_type}")
            raise HTTPException(status_code=400, detail=f"Unknown event type: {payload.event_type}")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"3CX webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/webhook/postcall")
async def postcall_webhook_endpoint(
    request: Request,
    elevenlabs_signature: str = Header(None, alias="elevenlabs-signature")
):
    """
    ElevenLabs POST-call webhook endpoint.
    
    Handles post-call events including:
    - Call transcripts
    - Call duration
    - Call status (completed, failed, missed)
    
    Security:
    - HMAC signature validation via elevenlabs-signature header
    
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
        if settings.webhook_secret:
            is_valid, error_message = hmac_validator.validate(elevenlabs_signature, body)
            if not is_valid:
                logger.warning(f"POST-call webhook HMAC validation failed: {error_message}")
                if "expired" in error_message.lower():
                    raise HTTPException(status_code=400, detail=error_message)
                raise HTTPException(status_code=401, detail=error_message)
        
        # Parse JSON payload
        import json
        try:
            payload_dict = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate with Pydantic model
        payload = PostCallWebhookPayload(**payload_dict)
        
        # Handle POST-call event
        result = await postcall_handler.handle(payload)
        
        return JSONResponse(content=result, status_code=200)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"POST-call webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def main():
    """Main entry point for running the service."""
    import uvicorn
    
    settings = get_settings()
    host = settings.host
    port = settings.port
    log_level = settings.log_level.lower()
    
    logger.info(f"Starting Voice Clone Pre-Call Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False
    )


if __name__ == "__main__":
    main()
