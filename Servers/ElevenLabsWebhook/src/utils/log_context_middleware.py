import uuid
import logging
from typing import Optional

from fastapi import Request
from starlette.responses import Response

from src.utils.logger import request_log_buffer, flush_logs
from src.utils.logger import setup_logger

logger = setup_logger()


async def log_context_middleware(request: Request, call_next) -> Response:
    """
    FastAPI HTTP middleware that:
    - Initializes request_log_buffer ContextVar at request start
    - Extracts conversation id from header `x-conversation-id`, or generates a UUID
    - Calls `flush_logs(conversation_id)` in the finally block
    - Resets ContextVars safely

    Fail-silent: any errors during logging should not affect the request
    """
    conversation_id: Optional[str] = request.headers.get("x-conversation-id")
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Initialize per-request buffer and keep token for reset
    token = request_log_buffer.set([])

    try:
        response = await call_next(request)
        return response
    finally:
        # Always attempt to flush logs, but swallow any errors
        try:
            flush_logs(conversation_id)
        except Exception:
            logger.exception("Failed to flush logs for conversation_id: %s", conversation_id)
        # Reset ContextVar to previous state to avoid leaks across requests
        try:
            request_log_buffer.reset(token)
        except Exception:
            # As a last resort, set to None
            request_log_buffer.set(None)