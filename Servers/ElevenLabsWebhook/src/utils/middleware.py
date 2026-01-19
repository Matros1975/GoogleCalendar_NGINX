import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.utils.logger import request_log_buffer, flush_logs



class RequestLogMiddleware(BaseHTTPMiddleware):
    """
    Controls request lifecycle.
    Ensures ONE blob per request.
    """

    async def dispatch(self, request: Request, call_next):
        conversation_id = request.headers.get(
            "x-conversation-id",
            f"req_{uuid.uuid4().hex}"
        )

        token = request_log_buffer.set([])

        try:
            response = await call_next(request)
            return response
        finally:
            flush_logs(conversation_id)
            request_log_buffer.reset(token)
