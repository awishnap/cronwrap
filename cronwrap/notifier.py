"""Notification backends for cronwrap alerts."""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for email notifications."""
    recipients: List[str]
    sender: str = "cronwrap@localhost"
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = False

    def __post_init__(self):
        if not self.recipients:
            raise ValueError("At least one recipient is required")
        if not all("@" in r for r in self.recipients):
            raise ValueError("All recipients must be valid email addresses")


class Notifier:
    """Sends email notifications for cron job events."""

    def __init__(self, config: NotificationConfig):
        self.config = config

    def notify_success(self, job_name: str, duration: float, output: str = "") -> bool:
        """Send a success notification."""
        subject = f"[cronwrap] SUCCESS: {job_name}"
        body = (
            f"Job '{job_name}' completed successfully.\n"
            f"Duration: {duration:.2f}s\n"
        )
        if output:
            body += f"\nOutput:\n{output}"
        return self._send(subject, body)

    def notify_failure(self, job_name: str, exit_code: int,
                       error_output: str = "", attempts: int = 1) -> bool:
        """Send a failure notification."""
        subject = f"[cronwrap] FAILURE: {job_name}"
        body = (
            f"Job '{job_name}' failed after {attempts} attempt(s).\n"
            f"Exit code: {exit_code}\n"
        )
        if error_output:
            body += f"\nError output:\n{error_output}"
        return self._send(subject, body)

    def _send(self, subject: str, body: str) -> bool:
        """Build and send an email message."""
        msg = MIMEMultipart()
        msg["From"] = self.config.sender
        msg["To"] = ", ".join(self.config.recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(
                    self.config.sender,
                    self.config.recipients,
                    msg.as_string(),
                )
            logger.debug("Notification sent: %s", subject)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Failed to send notification '%s': %s", subject, exc)
            return False
