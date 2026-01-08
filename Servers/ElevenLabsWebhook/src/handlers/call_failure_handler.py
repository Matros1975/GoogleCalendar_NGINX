"""
Handler for call_initiation_failure webhooks.

Handles:
- Failure metadata parsing
- SIP vs Twilio format handling
- Failure reason logging (busy, no-answer, unknown)
- Provider-specific details extraction
"""

import logging
from typing import Dict, Any, Optional

from src.models.webhook_models import CallFailurePayload
from src.utils.logger import conversation_context

logger = logging.getLogger(__name__)


class CallFailureHandler:
    """Handler for call_initiation_failure webhook events."""
    
    # Known failure reasons
    FAILURE_REASONS = {
        "busy": "The called party is busy",
        "no-answer": "The called party did not answer",
        "rejected": "The call was rejected",
        "invalid": "Invalid phone number or destination",
        "network_error": "Network connectivity issue",
        "unknown": "Unknown failure reason"
    }
    
    def __init__(self):
        """Initialize handler."""
        pass
    
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a call_initiation_failure webhook payload.
        
        Args:
            payload: Raw webhook payload dictionary
            
        Returns:
            Processing result dictionary
        """
        logger.info("Processing call_initiation_failure webhook")
        
        try:
            # Parse payload into typed model
            failure = CallFailurePayload.from_dict(payload)
            
            # Set conversation context for all subsequent log entries
            conversation_context.set(failure.conversation_id)
            
            logger.warning(
                f"Call initiation failed - "
                f"conversation_id: {failure.conversation_id}, "
                f"agent_id: {failure.agent_id}, "
                f"error: {failure.error_message}"
            )
            
            # Log provider-specific details
            self._log_provider_details(failure)
            
            return {
                "status": "processed",
                "conversation_id": failure.conversation_id,
                "agent_id": failure.agent_id,
                "error_message": failure.error_message,
                "error_code": failure.error_code,
                "provider": failure.provider
            }
            
        except Exception as e:
            logger.exception(f"Error processing call failure: {e}")
            raise
    
    def _log_provider_details(self, failure: CallFailurePayload) -> None:
        """
        Log provider-specific failure details.
        
        Args:
            failure: Parsed failure payload
        """
        if failure.error_code:
            logger.info(f"Error code: {failure.error_code}")
        
        if failure.provider:
            logger.info(f"Provider: {failure.provider}")
            
            if failure.provider.lower() == "sip":
                self._log_sip_details(failure.provider_details)
            elif failure.provider.lower() == "twilio":
                self._log_twilio_details(failure.provider_details)
        
        if failure.provider_details:
            logger.debug(f"Provider details: {failure.provider_details}")
    
    def _log_sip_details(self, details: Dict[str, Any]) -> None:
        """
        Log SIP-specific failure details.
        
        Args:
            details: SIP provider details dictionary
        """
        if not details:
            return
        
        sip_code = details.get("sip_code")
        sip_reason = details.get("sip_reason")
        
        if sip_code:
            logger.info(f"SIP status code: {sip_code}")
        if sip_reason:
            logger.info(f"SIP reason: {sip_reason}")
    
    def _log_twilio_details(self, details: Dict[str, Any]) -> None:
        """
        Log Twilio-specific failure details.
        
        Args:
            details: Twilio provider details dictionary
        """
        if not details:
            return
        
        error_code = details.get("error_code")
        error_message = details.get("error_message")
        call_status = details.get("call_status")
        
        if error_code:
            logger.info(f"Twilio error code: {error_code}")
        if error_message:
            logger.info(f"Twilio error message: {error_message}")
        if call_status:
            logger.info(f"Twilio call status: {call_status}")
    
    def get_failure_description(self, reason: str) -> str:
        """
        Get human-readable description for a failure reason.
        
        Args:
            reason: Failure reason code
            
        Returns:
            Human-readable description
        """
        return self.FAILURE_REASONS.get(
            reason.lower(),
            self.FAILURE_REASONS["unknown"]
        )
