"""Bearer token validator matching GoogleCalendarMCP pattern."""

import re
from typing import Set, List


class BearerTokenValidator:
    """Validates bearer tokens for MCP authentication."""
    
    def __init__(self, tokens: List[str]):
        """Initialize validator with list of valid tokens.
        
        Args:
            tokens: List of valid bearer token strings
        """
        self.valid_tokens: Set[str] = set(tokens)
    
    def validate_token(self, token: str) -> bool:
        """Validate a bearer token.
        
        Args:
            token: Token string, optionally with 'Bearer ' prefix
            
        Returns:
            True if token is valid, False otherwise
        """
        if not token:
            return False
        
        # Remove 'Bearer ' prefix if present (case-insensitive)
        clean_token = re.sub(r'^Bearer\s+', '', token, flags=re.IGNORECASE)
        
        return clean_token in self.valid_tokens
    
    def add_token(self, token: str) -> None:
        """Add a new token at runtime.
        
        Args:
            token: Token string to add
        """
        self.valid_tokens.add(token)
    
    def remove_token(self, token: str) -> None:
        """Remove a token at runtime.
        
        Args:
            token: Token string to remove
        """
        self.valid_tokens.discard(token)
