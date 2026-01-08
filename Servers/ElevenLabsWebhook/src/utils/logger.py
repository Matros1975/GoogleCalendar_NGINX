import os
import logging
from datetime import datetime
from typing import List
from contextvars import ContextVar

from azure.storage.blob import BlobServiceClient, ContentSettings

# Backward-compatibility for existing tests (no functional use)
conversation_context: ContextVar[str] = ContextVar(
    "conversation_context",
    default="N/A"
)

# Request-scoped log buffer
request_log_buffer: ContextVar[List[str]] = ContextVar(
    "request_log_buffer",
    default=None
)


class AzureBlobHandler(logging.Handler):
    """
    Buffers logs per request.
    Upload is triggered by middleware at request end.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            buf = request_log_buffer.get()
            if buf is not None:
                buf.append(self.format(record))
        except Exception:
            pass


def setup_logger(name: str = "fastapi-test") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Allow multiple calls, but avoid duplicate handlers
    if any(isinstance(h, AzureBlobHandler) for h in logger.handlers):
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Azure handler
    if os.getenv("AzureWebJobsStorage_elevenlabswebhook") and os.getenv("BLOB_CONTAINER_NAME"):
        blob_handler = AzureBlobHandler()
        blob_handler.setFormatter(formatter)
        logger.addHandler(blob_handler)

    logger.propagate = False
    return logger


def flush_logs(conversation_id: str):
    """
    Upload ONE blob for the current request.

    Notes:
    - Fail silently on any error (must never break request handling)
    - Use environment var BLOB_PREFIX (default: "logs") for top-level folder
    - No I/O should occur inside AzureBlobHandler.emit; all I/O happens here
    """
    buffer = request_log_buffer.get()
    if not buffer:
        return

    conn = os.getenv("AzureWebJobsStorage_elevenlabswebhook")
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    if not conn or not container_name:
        # Required env vars missing - nothing to do
        return

    prefix = os.getenv("BLOB_PREFIX", "logs").strip("/")

    try:
        service = BlobServiceClient.from_connection_string(conn)
        container = service.get_container_client(container_name)

        try:
            container.create_container()
        except Exception:
            # container may already exist or creation not permitted - continue
            pass

        now = datetime.utcnow()

        # Folder structure
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        timestamp = now.strftime("%Y%m%dT%H%M%S%f")

        blob_name = (
            f"{prefix}/{year}/{month}/{day}/"
            f"{timestamp}_{conversation_id}.log"
        )

        blob = container.get_blob_client(blob_name)
        blob.upload_blob(
            "\n".join(buffer).encode("utf-8"),
            overwrite=True,
            content_settings=ContentSettings(content_type="text/plain"),
        )

    except Exception:
        # Must never raise - swallow any Azure errors
        logging.getLogger(__name__).exception("Failed to upload logs to Azure Blob Storage")
        return
