import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications"""

    def __init__(self, config):
        self.config = config
        self.enabled = config.SMTP_ENABLED

    def send_thumbs_down_notification(self, document_id, ip_address=None, user_agent=None):
        """Send email notification when a document receives thumbs down"""
        if not self.enabled:
            logger.info(f"Email disabled - Would send thumbs down notification for document: {document_id}")
            return False

        subject = f"Thumbs Down Received - Document {document_id}"

        body = f"""
A document has received a thumbs down feedback.

Document ID: {document_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
IP Address: {ip_address or 'Unknown'}
User Agent: {user_agent or 'Unknown'}

Please review this document and consider improvements.
"""

        return self.send_email(
            to_email=self.config.SMTP_TO,
            subject=subject,
            body=body
        )

    def send_email(self, to_email, subject, body, html_body=None):
        """Send an email via SMTP"""
        if not self.enabled:
            logger.warning("SMTP is not enabled. Email not sent.")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config.SMTP_FROM
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT) as server:
                if self.config.SMTP_USE_TLS:
                    server.starttls()

                if self.config.SMTP_USER and self.config.SMTP_PASSWORD:
                    server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)

                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
