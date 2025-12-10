"""
Logging configuration for Voice Clone Pre-Call Service.
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar

# Context variable to store call_id across async calls
call_context: ContextVar[str] = ContextVar('call_id', default='N/A')


class CallFilter(logging.Filter):
    """Add call_id to all log records from context."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Inject call_id into log record."""
        record.call_id = call_context.get()
        return True


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
    """Standard text formatter for human-readable logs with call_id."""
    
    def __init__(self):
        """Initialize formatter."""
        super().__init__(
            fmt="%(asctime)s - [%(call_id)s] - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logger(
    name: str = None,
    level: str = None,
    log_format: str = None
) -> logging.Logger:
    """
    Set up and configure logger with file rotation.
    
    Args:
        name: Logger name (defaults to root logger)
        level: Log level (defaults to LOG_LEVEL env var or INFO)
        log_format: Log format ("json" or "text", defaults to LOG_FORMAT env var or "text")
        
    Returns:
        Configured logger instance with both console and file handlers
    """
    # Get configuration from environment
    level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "text").lower()
    log_dir = os.getenv("LOG_DIR", "/var/log/voiceclone-precall")
    log_filename = os.getenv("LOG_FILENAME", "voiceclone.log")
    
    # Get or create logger
    logger = logging.getLogger(name)
    
    # Check if this specific logger (or root) is already configured
    check_logger = logging.getLogger() if name is None else logger
    
    # If root logger has handlers with file output, we're already configured
    has_file_handler = any(
        hasattr(h, 'baseFilename') for h in logging.getLogger().handlers
    )
    
    if has_file_handler and name is not None:
        # Root logger is configured with file handler, child loggers will inherit
        return logger
    
    if check_logger.handlers and name is None:
        # Root logger already has handlers, don't add duplicates
        return logger
    
    # Set level
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Set formatter based on format
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = StandardFormatter()
    
    # Create call filter (will be added to each handler)
    call_filter = CallFilter()
    
    # Create console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level, logging.INFO))
    console_handler.addFilter(call_filter)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler with rotation
    try:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, log_filename)
        
        # Extract base name without extension for rotated files
        base_name = os.path.splitext(log_filename)[0]
        
        # Custom flushing handler for immediate log visibility
        class FlushingHandler(RotatingFileHandler):
            def emit(self, record):
                super().emit(record)
                self.flush()
        
        # RotatingFileHandler with 2MB max size
        flushing_handler = FlushingHandler(
            log_file,
            maxBytes=2 * 1024 * 1024,  # 2MB
            backupCount=10  # Keep up to 10 old log files
        )
        
        # Custom namer to add timestamp instead of .1, .2, etc.
        def namer(default_name):
            """Add timestamp to rotated log files."""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{log_dir}/{base_name}_{timestamp}.log"
        
        flushing_handler.namer = namer
        flushing_handler.setLevel(getattr(logging, level, logging.INFO))
        flushing_handler.addFilter(call_filter)
        flushing_handler.setFormatter(formatter)
        logger.addHandler(flushing_handler)
        
    except (OSError, PermissionError) as e:
        # If file logging fails (permissions, disk full, etc.), log to console only
        logger.warning(f"Failed to setup file logging: {e}. Logging to console only.")
    
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
