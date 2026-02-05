"""
Email notification sender for error cases.

Sends email notifications via Gmail SMTP when ticket creation fails.
"""

import os
import json
from email.message import EmailMessage
from typing import Optional
import aiosmtplib
from src.utils.logger import setup_logger


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
            ticket_data: Extracted ticket data
            payload: Original webhook payload
            call_number: Caller's phone number
            call_time: Call timestamp
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

        <p><strong style="font-size:14pt;">Ticket cannot be created at TopDesk environment:</strong><br>
        {topdesk_env}</p>

        <p><strong style="font-size:14pt;">Due to the following error:</strong><br>
        {error_message}</p>

        <p><strong style="font-size:14pt;">Ticket details:</strong></p>
        <pre>{ticket_details}</pre>

        <p><strong style="font-size:14pt;">Call Transcript:</strong></p>
        <pre>{transcript}</pre>

        <p><em>Full agent payload is attached as JSON.</em></p>
        """

        message.set_content("This is an automated notification. Please see the HTML version.")
        message.add_alternative(body, subtype="html")

        # JSON attachment instead of XML
        try:
            # Pretty print JSON for readability
            json_payload = json.dumps(payload, indent=2, ensure_ascii=False)
            message.add_attachment(
                json_payload.encode("utf-8"),
                maintype="application",
                subtype="json",
                filename="agent_payload.json"
            )
        except Exception as json_error:
            logger.error(f"Failed to create JSON attachment: {json_error}")
            # Add a simple text attachment with error message
            error_text = f"Failed to serialize payload to JSON: {json_error}\n\nOriginal error: {error_message}"
            message.add_attachment(
                error_text.encode("utf-8"),
                maintype="text",
                subtype="plain",
                filename="error_details.txt"
            )
        
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