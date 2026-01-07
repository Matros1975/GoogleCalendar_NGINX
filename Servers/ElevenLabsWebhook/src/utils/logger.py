import logging
from src.utils.log_context import request_log_buffer


class RequestBufferLogHandler(logging.Handler):
    def emit(self, record):
        try:
            buffer = request_log_buffer.get()
            if buffer is None:
                return

            buffer.append(self.format(record))
        except Exception:
            # Logging must NEVER crash the app
            pass


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("ElevenLabsWebhook")
    logger.setLevel(logging.INFO)

    if any(isinstance(h, RequestBufferLogHandler) for h in logger.handlers):
        return logger

    handler = RequestBufferLogHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger
