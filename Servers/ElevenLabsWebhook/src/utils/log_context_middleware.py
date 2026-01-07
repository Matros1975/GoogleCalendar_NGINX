from datetime import datetime
from uuid import uuid4
from fastapi import Request
from src.utils.log_context import request_log_buffer
from src.utils.blob_writer import write_logs_to_blob


async def log_context_middleware(request: Request, call_next):
    buffer: list[str] = []
    token = request_log_buffer.set(buffer)

    now = datetime.utcnow()
    request_id = uuid4().hex

    blob_name = (
        f"logs/{now.year}/{now.month:02d}/{now.day:02d}/"
        f"webhook_{now.strftime('%Y%m%d_%H%M%S')}_{request_id}.log"
    )

    try:
        response = await call_next(request)
        return response
    finally:
        request_log_buffer.reset(token)

        if buffer:
            write_logs_to_blob(blob_name, buffer)
