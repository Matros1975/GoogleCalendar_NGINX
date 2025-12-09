"""
Email notification sender for error cases.

Sends email notifications via Gmail SMTP when ticket creation fails.
# testing #3
"""

import os
import logging
from email.message import EmailMessage
from typing import Optional

import aiosmtplib


logger = logging.getLogger(__name__)


class EmailSender:
    """Send email notifications via Gmail SMTP."""
    
    def __init__(self):
        """Initialize email sender from environment variables."""
        self.smtp_host = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        self.username = os.getenv("GMAIL_SMTP_USERNAME", "")
        self.password = os.getenv("GMAIL_SMTP_PASSWORD", "")
        self.from_address = os.getenv("GMAIL_FROM_ADDRESS", "")
        self.default_to_address = os.getenv("SERVICEDESK_EMAIL", "")
    
    def is_configured(self) -> bool:
        """Check if email sender is properly configured."""
        return bool(self.username and self.password and self.from_address)
    
    async def send_error_notification(
        self,
        conversation_id: str,
        transcript: str,
        error_message: str,
        to_address: Optional[str] = None
    ) -> bool:
        """
        Send email notification when ticket creation fails.
        
        Args:
            conversation_id: ElevenLabs conversation ID
            transcript: Call transcript
            error_message: Error details
            to_address: Recipient email (defaults to SERVICEDESK_EMAIL)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email sender not configured, cannot send notification")
            return False
        
        to_address = to_address or self.default_to_address
        
        message = EmailMessage()
        message["From"] = self.from_address
        message["To"] = to_address
        message["Subject"] = f"[ElevenLabs] Failed to create ticket - {conversation_id}"
        
        body = f"""A call transcript could not be processed into a TopDesk ticket.

Conversation ID: {conversation_id}
Error: {error_message}

Call Transcript:
----------------
{transcript}

Please create a ticket manually.
"""
        message.set_content(body)
        
        try:
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.username,
                password=self.password,
                start_tls=True
            )
            logger.info(f"Error notification sent to {to_address} for {conversation_id}")
            return True
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
