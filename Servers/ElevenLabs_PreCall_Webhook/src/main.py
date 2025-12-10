"""
Main entry point for ElevenLabs Pre-Call Webhook Service.

This service handles pre-call webhooks from ElevenLabs for:
- Voice sample processing
- Instant voice cloning
- Agent configuration updates
"""

import json
import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse

from src.auth.hmac_validator import HMACValidator
from src.handlers.precall_handler import PreCallHandler
from src.services.elevenlabs_client import ElevenLabsAPIClient
from src.services.voice_cloning_service import VoiceCloningService
from src.utils.logger import setup_logger
from src.utils.file_handler import FileHandler
from src.models.webhook_models import (
    PreCallWebhookResponse,
    PreCallWebhookError
)

# Setup logging
logger = setup_logger()

# Initialize components (will be configured on startup)
hmac_validator: HMACValidator = None
precall_handler: PreCallHandler = None
file_handler: FileHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global hmac_validator, precall_handler, file_handler
    
    # Startup
    webhook_secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    
    if not webhook_secret:
        logger.warning("ELEVENLABS_WEBHOOK_SECRET not set - HMAC validation will fail")
    
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not set - voice cloning will fail")
    
    # Initialize components
    hmac_validator = HMACValidator(secret=webhook_secret)
    
    # File handler
    storage_path = os.getenv("VOICE_SAMPLE_STORAGE_PATH", "/app/storage/voice_samples")
    enable_storage = os.getenv("ENABLE_VOICE_SAMPLE_STORAGE", "false").lower() == "true"
    file_handler = FileHandler(storage_path=storage_path, enable_storage=enable_storage)
    
    # ElevenLabs client
    elevenlabs_client = ElevenLabsAPIClient(api_key=api_key)
    
    # Voice cloning service
    min_duration = float(os.getenv("VOICE_CLONE_MIN_DURATION", "3.0"))
    max_size_mb = float(os.getenv("VOICE_CLONE_MAX_SIZE_MB", "10.0"))
    voice_service = VoiceCloningService(
        elevenlabs_client=elevenlabs_client,
        file_handler=file_handler,
        min_duration=min_duration,
        max_size_mb=max_size_mb
    )
    
    # Pre-call handler
    default_message = os.getenv("DEFAULT_FIRST_MESSAGE", "Hallo {name}, fijn dat je belt!")
    precall_handler = PreCallHandler(
        voice_cloning_service=voice_service,
        file_handler=file_handler,
        default_first_message=default_message
    )
    
    logger.info("ElevenLabs Pre-Call Webhook Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("ElevenLabs Pre-Call Webhook Service shutting down...")


# Initialize FastAPI app with lifespan handler
app = FastAPI(
    title="ElevenLabs Pre-Call Webhook Service",
    version="1.0.0",
    description="Webhook receiver for ElevenLabs pre-call events with voice cloning",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/NGINX monitoring."""
    return {"status": "healthy", "service": "elevenlabs-precall-webhook"}


@app.post("/webhook")
async def webhook_endpoint(
    request: Request,
    elevenlabs_signature: str = Header(None, alias="elevenlabs-signature"),
    metadata: str = Form(None),
    voice_sample: UploadFile = File(None)
):
    """
    Main webhook endpoint for ElevenLabs pre-call webhooks.
    
    Supports two payload formats:
    1. JSON: application/json with base64-encoded voice sample
    2. Multipart: multipart/form-data with file upload
    
    Returns:
        200 OK for successful processing
        400 Bad Request for invalid payloads
        401 Unauthorized for invalid signatures
        422 Unprocessable Entity for voice cloning failures
        500 Internal Server Error for processing failures
    """
    try:
        # Check content type
        content_type = request.headers.get("content-type", "")
        
        if "multipart/form-data" in content_type:
            # Multipart form data
            if not metadata:
                raise HTTPException(status_code=400, detail="Missing metadata field")
            
            # Parse metadata JSON
            try:
                payload = json.loads(metadata)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in metadata field: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON in metadata field")
            
            # Get voice sample file
            if not voice_sample:
                raise HTTPException(status_code=400, detail="Missing voice_sample file")
            
            voice_sample_bytes = await voice_sample.read()
            
            # For multipart, we can't validate HMAC on the body directly
            # We'll validate on the metadata field
            metadata_bytes = metadata.encode("utf-8")
            is_valid, error_message = hmac_validator.validate(elevenlabs_signature, metadata_bytes)
            
            if not is_valid:
                logger.warning(f"HMAC validation failed: {error_message}")
                if "expired" in error_message.lower():
                    raise HTTPException(status_code=400, detail=error_message)
                raise HTTPException(status_code=401, detail=error_message)
        
        else:
            # JSON payload
            body = await request.body()
            
            # Validate HMAC signature
            is_valid, error_message = hmac_validator.validate(elevenlabs_signature, body)
            if not is_valid:
                logger.warning(f"HMAC validation failed: {error_message}")
                if "expired" in error_message.lower():
                    raise HTTPException(status_code=400, detail=error_message)
                raise HTTPException(status_code=401, detail=error_message)
            
            # Parse JSON payload
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON payload: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            
            voice_sample_bytes = None  # Will be extracted from payload
        
        # Validate webhook type
        webhook_type = payload.get("type")
        if webhook_type != "pre_call":
            logger.error(f"Invalid webhook type: {webhook_type}")
            raise HTTPException(status_code=400, detail=f"Invalid webhook type: {webhook_type}")
        
        # Process webhook
        try:
            result = await precall_handler.handle(payload, voice_sample_bytes)
            
            response = PreCallWebhookResponse(
                status="success",
                **result
            )
            
            logger.info(f"Successfully processed pre_call webhook")
            return JSONResponse(content=response.model_dump(), status_code=200)
            
        except ValueError as e:
            # Validation errors (400 or 422)
            error_response = PreCallWebhookError(
                error_code="VALIDATION_ERROR",
                error_message=str(e),
                conversation_id=payload.get("conversation_id")
            )
            logger.warning(f"Validation error: {str(e)}")
            return JSONResponse(content=error_response.model_dump(), status_code=400)
            
        except Exception as e:
            # Voice cloning or processing errors
            error_response = PreCallWebhookError(
                error_code="VOICE_CLONING_FAILED",
                error_message=str(e),
                conversation_id=payload.get("conversation_id")
            )
            logger.error(f"Voice cloning failed: {str(e)}")
            return JSONResponse(content=error_response.model_dump(), status_code=422)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def main():
    """Main entry point for running the service."""
    import uvicorn
    
    host = os.getenv("PRECALL_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("PRECALL_WEBHOOK_PORT", "3005"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    logger.info(f"Starting ElevenLabs Pre-Call Webhook Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False
    )


if __name__ == "__main__":
    main()
