from contextvars import ContextVar

request_log_buffer: ContextVar[list[str] | None] = ContextVar(
    "request_log_buffer",
    default=None
)
