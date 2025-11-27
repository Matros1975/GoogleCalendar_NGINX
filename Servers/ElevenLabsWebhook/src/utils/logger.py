"""
Logging configuration for ElevenLabs Webhook Service.
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
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
    """Standard text formatter for human-readable logs."""
    
    def __init__(self):
        """Initialize formatter."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logger(
    name: str = None,
    level: str = None,
    log_format: str = None
) -> logging.Logger:
    """
    Set up and configure logger.
    
    Args:
        name: Logger name (defaults to root logger)
        level: Log level (defaults to LOG_LEVEL env var or INFO)
        log_format: Log format ("json" or "text", defaults to LOG_FORMAT env var or "text")
        
    Returns:
        Configured logger instance
    """
    # Get configuration from environment
    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "text").lower()
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Don't add handlers if already configured
    if logger.handlers:
        return logger
    
    # Set level
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level, logging.INFO))
    
    # Set formatter based on format
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = StandardFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
