"""
Main entry point for ElevenLabs Webhook Service.

This service handles post-call webhooks from ElevenLabs including:
- post_call_transcription: Full conversation data with transcripts
- post_call_audio: Base64-encoded MP3 audio
- call_initiation_failure: Failed call metadata
"""

import json
import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from src.auth.hmac_validator import HMACValidator
from src.handlers.transcription_handler import TranscriptionHandler
from src.handlers.audio_handler import AudioHandler
from src.handlers.call_failure_handler import CallFailureHandler
from src.utils.logger import setup_logger
from src.utils.log_context_middleware import log_context_middleware

# Setup logging
logger = setup_logger()

# Initialize components (will be configured on startup)
hmac_validator: HMACValidator = None
transcription_handler: TranscriptionHandler = None
audio_handler: AudioHandler = None
call_failure_handler: CallFailureHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global hmac_validator, transcription_handler, audio_handler, call_failure_handler
    
    # Startup
    secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning("ELEVENLABS_WEBHOOK_SECRET not set - HMAC validation will fail")
    
    hmac_validator = HMACValidator(secret=secret)
    transcription_handler = TranscriptionHandler()
    audio_handler = AudioHandler()
    call_failure_handler = CallFailureHandler()
    
    logger.info("ElevenLabs Webhook Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("ElevenLabs Webhook Service shutting down...")


# Initialize FastAPI app with lifespan handler
app = FastAPI(
    title="ElevenLabs Webhook Service",
    version="1.0.0",
    description="Webhook receiver for ElevenLabs post-call events",
    lifespan=lifespan
)

# Attach request log context middleware to the final app instance
app.middleware("http")(log_context_middleware)

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/NGINX monitoring."""
    return {"status": "healthy", "service": "elevenlabs-webhook"}


@app.post("/webhook")
async def webhook_endpoint(
    request: Request,
    elevenlabs_signature: str = Header(None, alias="elevenlabs-signature")
):
    """
    Main webhook endpoint for ElevenLabs post-call webhooks.
    
    Handles three types:
    - post_call_transcription: Full conversation data with transcripts
    - post_call_audio: Base64-encoded MP3 audio
    - call_initiation_failure: Failed call metadata
    
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
        
        # Route to appropriate handler based on type
        webhook_type = payload.get("type")
        
        if webhook_type == "post_call_transcription":
            result = await transcription_handler.handle(payload)
        elif webhook_type == "post_call_audio":
            result = await audio_handler.handle(payload)
        elif webhook_type == "call_initiation_failure":
            result = await call_failure_handler.handle(payload)
        else:
            logger.error(f"Unknown webhook type: {webhook_type}")
            raise HTTPException(
                status_code=400,
                detail=f"Unknown webhook type: {webhook_type}"
            )

        logger.info(f"Successfully processed {webhook_type} webhook")
        return JSONResponse(content={"status": "received"}, status_code=200)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def main():
    """Main entry point for running the service."""
    import uvicorn
    
    host = os.getenv("ELEVENLABS_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("ELEVENLABS_WEBHOOK_PORT", "3004"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    logger.info(f"Starting ElevenLabs Webhook Service on {host}:{port}")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False
    )


if __name__ == "__main__":
    main()
