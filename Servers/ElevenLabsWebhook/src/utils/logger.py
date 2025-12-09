"""
Logging configuration for ElevenLabs Webhook Service.
"""

import os
import sys
import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar
import traceback
from azure.storage.blob import BlobServiceClient

# --------- NEW: RUN ID (unique for each execution) ----------
RUN_ID = str(int(datetime.utcnow().timestamp()))   # e.g., 1764940268

# Context variable to store conversation_id across async calls
conversation_context: ContextVar[str] = ContextVar('conversation_id', default='N/A')


class ConversationFilter(logging.Filter):
    """Add conversation_id to all log records from context."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.conversation_id = conversation_context.get()
        return True


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "taskName", "message"
            ):
                log_obj[key] = value
        
        return json.dumps(log_obj)


class StandardFormatter(logging.Formatter):
    """Standard text formatter for human-readable logs with conversation_id."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - [%(conversation_id)s] - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# ---------------------- AZURE BLOB STORAGE SETUP ----------------------
connect_str = os.getenv("AzureWebJobsStorage_elevenlabswebhook") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_container = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")
blob_service_client = None

if connect_str:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    except Exception as e:
        print("Blob init error:", e)


class BlobUploadHandler(logging.Handler):
    """Uploads log records into ONE file for the entire execution run."""

    def emit(self, record):
        try:
            if not blob_service_client or not blob_container:
                return

            msg = self.format(record)
            now = datetime.utcnow()

            # Folder: logs/YYYY/MM/DD/
            folder = f"logs/{now.year}/{now.month:02d}/{now.day:02d}"

            # ------------ UPDATED: ONE FILE PER EXECUTION RUN ----------------
            blob_name = f"{folder}/webhook_run_{RUN_ID}.log"

            container_client = blob_service_client.get_container_client(blob_container)
            if not container_client.exists():
                container_client.create_container()

            blob_client = container_client.get_blob_client(blob_name)

            # Append content
            try:
                old_content = blob_client.download_blob().readall().decode("utf-8")
            except Exception:
                old_content = ""

            new_content = old_content + msg + "\n"
            blob_client.upload_blob(new_content, overwrite=True)

        except Exception:
            print("Blob upload failed:", record.getMessage())


# -------------------------------------------------------------------


def setup_logger(
    name: str = None,
    level: str = None,
    log_format: str = None
) -> logging.Logger:

    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "text").lower()

    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    formatter = JSONFormatter() if log_format == "json" else StandardFormatter()
    conversation_filter = ConversationFilter()
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level, logging.INFO))
    console_handler.addFilter(conversation_filter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Blob Handler
    if blob_service_client:
        try:
            blob_handler = BlobUploadHandler()
            blob_handler.setLevel(getattr(logging, level, logging.INFO))
            blob_handler.setFormatter(formatter)
            blob_handler.addFilter(conversation_filter)
            logger.addHandler(blob_handler)
        except Exception as e:
            logger.warning(f"Failed to setup blob logging: {e}")

    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
