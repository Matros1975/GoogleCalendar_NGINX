"""Tool handlers for TopDesk MCP."""

from .incidents import IncidentHandlers
from .persons import PersonHandlers
from .status import StatusHandlers

__all__ = ["IncidentHandlers", "PersonHandlers", "StatusHandlers"]
