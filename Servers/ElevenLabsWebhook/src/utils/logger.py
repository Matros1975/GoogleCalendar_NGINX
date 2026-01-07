"""
Logging configuration for ElevenLabs Webhook Service.
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar
from uuid import uuid4
from azure.storage.blob import BlobServiceClient

# ==========================================================
# CONTEXT VARIABLES (REQUEST SCOPED)
# ==========================================================
conversation_context: ContextVar[str] = ContextVar(
    "conversation_id",
    default="SYSTEM"
)

invocation_context: ContextVar[str | None] = ContextVar(
    "invocation_id",
    default=None
)

# ==========================================================
# FILTER
# ==========================================================
class ConversationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.conversation_id = conversation_context.get()
        record.invocation_id = invocation_context.get()
        return True

# ==========================================================
# FORMATTERS
# ==========================================================
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "conversation_id": record.conversation_id,
            "invocation_id": record.invocation_id,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class StandardFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            "%(asctime)s - [%(conversation_id)s] - %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

# ==========================================================
# AZURE BLOB INIT
# ==========================================================
connect_str = (
    os.getenv("AzureWebJobsStorage_elevenlabswebhook")
    or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)

blob_container = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")
blob_service_client = None

if connect_str:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    except Exception as e:
        print("Blob init error:", e)

# ==========================================================
# BLOB HANDLER (ONE FILE PER INVOCATION)
# ==========================================================
class BlobUploadHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            if not blob_service_client:
                return

            invocation_id = record.invocation_id
            if not invocation_id:
                return  # skip logs outside request scope

            msg = self.format(record) + "\n"
            now = datetime.utcnow()

            folder = f"logs/{now.year}/{now.month:02d}/{now.day:02d}"
            blob_name = f"{folder}/webhook_{invocation_id}.log"

            container = blob_service_client.get_container_client(blob_container)
            if not container.exists():
                container.create_container()

            blob = container.get_blob_client(blob_name)

            # Create append blob once
            if not blob.exists():
                blob.create_append_blob()

            blob.append_block(msg.encode("utf-8"))

        except Exception:
            # Logging must NEVER break the app
            pass

# ==========================================================
# LOGGER SETUP
# ==========================================================
def setup_logger(
    name: str | None = None,
    level: str | None = None,
    log_format: str | None = None,
    **kwargs
) -> logging.Logger:

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = StandardFormatter()
    filter_ = ConversationFilter()

    # Console logging
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(filter_)
    logger.addHandler(console)

    # Blob logging
    if blob_service_client:
        blob_handler = BlobUploadHandler()
        blob_handler.setFormatter(formatter)
        blob_handler.addFilter(filter_)
        logger.addHandler(blob_handler)

    logger.propagate = False
    return logger

# ==========================================================
# INVOCATION HELPERS (SAFE WITH EXISTING main.py)
# ==========================================================
def start_invocation(conversation_id: str | None = None) -> None:
    """
    Safe to call multiple times per request.
    - invocation_id is created ONLY ONCE
    - conversation_id may be updated later
    """

    # Create invocation only once
    if invocation_context.get() is None:
        invocation_context.set(
            datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            + "_"
            + uuid4().hex[:6]
        )

    # Conversation ID may arrive after payload parsing
    if conversation_id:
        conversation_context.set(conversation_id)


def end_invocation() -> None:
    invocation_context.set(None)
