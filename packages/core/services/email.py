"""Email service for sending notifications with input sanitization."""

import asyncio
import html
import re
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import structlog

from packages.core.config import settings


class EmailSendError(Exception):
    """Raised when email sending fails."""

    def __init__(self, message: str, to_email: str, original_error: Exception | None = None):
        self.to_email = to_email
        self.original_error = original_error
        super().__init__(message)


logger = structlog.get_logger()


def sanitize_email_input(text: str | None, max_length: int = 1000) -> str:
    """
    Sanitize text for use in email headers and body.

    Prevents email header injection and removes dangerous content.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for email use
    """
    if not text:
        return ""

    # Convert to string if needed
    text = str(text)

    # Remove control characters (including newlines in headers)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Prevent email header injection
    # Remove CRLF sequences that could inject new headers
    text = re.sub(r'\r\n|\r|\n', ' ', text)

    # Remove potential header injection patterns
    text = re.sub(r'(?i)(content-type|bcc|cc|to|from|subject|reply-to):', '[REMOVED]:', text)

    # Truncate to max length
    text = text[:max_length].strip()

    return text


def sanitize_email_address(email: str | None) -> str | None:
    """
    Validate and sanitize an email address.

    Returns None if the email is invalid or contains suspicious characters.
    For security, we reject emails that contain control characters rather
    than trying to sanitize them, as this could indicate an attack attempt.
    """
    if not email:
        return None

    # Basic sanitization
    email = email.strip().lower()

    # Reject emails with control characters (don't sanitize - reject for security)
    if re.search(r'[\x00-\x1f\x7f]', email):
        logger.warning("email_address_contains_control_chars", email=repr(email[:50]))
        return None

    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        logger.warning("email_address_invalid", email=email[:50])
        return None

    # Check for suspicious patterns
    if '..' in email or email.startswith('.') or email.endswith('.'):
        logger.warning("email_address_suspicious", email=email[:50])
        return None

    return email


def sanitize_html_body(html_content: str | None, max_length: int = 50000) -> str:
    """
    Sanitize HTML content for email body.

    Allows safe HTML but removes scripts and dangerous elements.
    """
    if not html_content:
        return ""

    # Remove script tags and their content
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # Remove style tags (can be used for tracking)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # Remove event handlers
    html_content = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)

    # Remove javascript: URLs
    html_content = re.sub(r'javascript:', 'blocked:', html_content, flags=re.IGNORECASE)

    # Truncate
    return html_content[:max_length]


class EmailService(ABC):
    """Abstract base class for email services."""

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            from_email: Optional sender (defaults to settings.from_email)
            reply_to: Optional reply-to address
            attachments: Optional list of attachments

        Returns:
            bool: True if sent successfully
        """
        pass

    @abstractmethod
    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, bool]:
        """
        Send email to multiple recipients.

        Returns:
            dict: Mapping of email -> success status
        """
        pass


class SMTPEmailService(EmailService):
    """SMTP-based email service."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        raise_on_error: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.raise_on_error = raise_on_error
        self.logger = logger.bind(service="email", backend="smtp")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send an email via SMTP with input sanitization."""
        # Sanitize all inputs (NEW-016 fix)
        sanitized_to = sanitize_email_address(to_email)
        if not sanitized_to:
            self.logger.error("email_invalid_recipient", to_email=to_email[:50])
            return False

        sanitized_subject = sanitize_email_input(subject, max_length=200)
        sanitized_body = sanitize_email_input(body, max_length=50000)
        sanitized_html = sanitize_html_body(html_body) if html_body else None

        from_addr = from_email or settings.from_email
        sanitized_from = sanitize_email_address(from_addr) or settings.from_email
        sanitized_reply_to = sanitize_email_address(reply_to) if reply_to else None

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = sanitized_subject
        msg["From"] = sanitized_from
        msg["To"] = sanitized_to

        if sanitized_reply_to:
            msg["Reply-To"] = sanitized_reply_to

        # Add plain text body
        msg.attach(MIMEText(sanitized_body, "plain"))

        # Add HTML body if provided
        if sanitized_html:
            msg.attach(MIMEText(sanitized_html, "html"))

        # Send in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                self._send_smtp,
                sanitized_from,
                sanitized_to,
                msg.as_string(),
            )
            return result
        except Exception as e:
            self.logger.error(
                "smtp_send_failed",
                to_email=to_email,
                error=str(e),
            )
            if self.raise_on_error:
                raise EmailSendError(
                    f"Failed to send email to {to_email}: {e}",
                    to_email=to_email,
                    original_error=e,
                )
            return False

    def _send_smtp(
        self,
        from_addr: str,
        to_addr: str,
        message: str,
    ) -> bool:
        """Synchronous SMTP send (run in thread)."""
        try:
            if self.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls(context=context)
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    server.sendmail(from_addr, to_addr, message)
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    server.sendmail(from_addr, to_addr, message)

            self.logger.info(
                "email_sent",
                to_email=to_addr,
            )
            return True

        except Exception as e:
            self.logger.error(
                "smtp_error",
                to_email=to_addr,
                error=str(e),
            )
            raise

    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, bool]:
        """Send email to multiple recipients."""
        results = {}
        for recipient in recipients:
            results[recipient] = await self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                html_body=html_body,
            )
        return results


class ConsoleEmailService(EmailService):
    """
    Console-based email service for development.

    Logs emails to console instead of sending them.
    """

    def __init__(self):
        self.logger = logger.bind(service="email", backend="console")
        self.sent_emails: list[dict[str, Any]] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Log email to console instead of sending."""
        from_addr = from_email or settings.from_email

        email_record = {
            "to": to_email,
            "from": from_addr,
            "subject": subject,
            "body": body,
            "html_body": html_body is not None,
            "reply_to": reply_to,
            "attachments": len(attachments) if attachments else 0,
        }

        self.sent_emails.append(email_record)

        self.logger.info(
            "email_logged",
            to_email=to_email,
            subject=subject,
        )

        print("\n" + "=" * 60)
        print("📧 EMAIL (Console Mode)")
        print("=" * 60)
        print(f"To: {to_email}")
        print(f"From: {from_addr}")
        print(f"Subject: {subject}")
        print("-" * 60)
        print(body)
        print("=" * 60 + "\n")

        return True

    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, bool]:
        """Log bulk emails to console."""
        results = {}
        for recipient in recipients:
            results[recipient] = await self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                html_body=html_body,
            )
        return results

    def get_sent_emails(self) -> list[dict[str, Any]]:
        """Get list of sent emails (for testing)."""
        return self.sent_emails

    def clear_sent_emails(self) -> None:
        """Clear sent emails list (for testing)."""
        self.sent_emails = []


class QueuedEmailService(EmailService):
    """
    Email service that queues emails for background processing.

    Uses the job queue to defer email sending.
    """

    def __init__(self, fallback_service: EmailService | None = None):
        self.logger = logger.bind(service="email", backend="queued")
        self.fallback = fallback_service or ConsoleEmailService()
        self.queue: list[dict[str, Any]] = []

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
        from_email: str | None = None,
        reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Queue email for background processing."""
        email_data = {
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "from_email": from_email or settings.from_email,
            "reply_to": reply_to,
        }

        self.queue.append(email_data)

        self.logger.info(
            "email_queued",
            to_email=to_email,
            subject=subject,
            queue_size=len(self.queue),
        )

        # In development, also log to console
        if settings.environment == "development":
            await self.fallback.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                html_body=html_body,
                from_email=from_email,
                reply_to=reply_to,
            )

        return True

    async def send_bulk_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, bool]:
        """Queue bulk emails."""
        results = {}
        for recipient in recipients:
            results[recipient] = await self.send_email(
                to_email=recipient,
                subject=subject,
                body=body,
                html_body=html_body,
            )
        return results

    async def process_queue(self, smtp_service: SMTPEmailService) -> dict[str, bool]:
        """Process queued emails (called by worker)."""
        results = {}

        while self.queue:
            email = self.queue.pop(0)
            try:
                success = await smtp_service.send_email(**email)
                results[email["to_email"]] = success
            except Exception as e:
                self.logger.error(
                    "queue_process_failed",
                    to_email=email["to_email"],
                    error=str(e),
                )
                results[email["to_email"]] = False
                # Re-queue failed emails
                self.queue.append(email)

        return results


# Service factory
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get the configured email service instance."""
    global _email_service

    if _email_service is not None:
        return _email_service

    if settings.environment == "development" or not settings.smtp_host:
        # Use console service in development
        _email_service = ConsoleEmailService()
    elif settings.smtp_user and settings.smtp_password:
        # Use SMTP service if credentials configured
        # In production, raise exceptions so failures are tracked/alerted
        _email_service = SMTPEmailService(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            raise_on_error=(settings.environment == "production"),
        )
    else:
        # Use queued service with console fallback
        logger.warning(
            "email_config_missing",
            message="SMTP credentials not configured - emails will be queued but not sent",
        )
        _email_service = QueuedEmailService()

    return _email_service


def reset_email_service() -> None:
    """Reset the email service (for testing)."""
    global _email_service
    _email_service = None
