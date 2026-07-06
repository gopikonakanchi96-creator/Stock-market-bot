from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from trading_bot.config.env import load_env_file


@dataclass(frozen=True)
class EmailResult:
    sent: bool
    reason: str


class EmailService:
    def __init__(self) -> None:
        load_env_file()
        self.host = os.getenv("SMTP_HOST")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.username or "")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    @property
    def configured(self) -> bool:
        return bool(self.host and self.port and self.username and self.password and self.from_email)

    def send_report(self, to_email: str, subject: str, body: str, attachment_path: str | Path | None = None) -> EmailResult:
        if not self.configured:
            return EmailResult(False, "SMTP is not configured; report PDF was generated locally only.")

        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        if attachment_path:
            path = Path(attachment_path)
            message.add_attachment(
                path.read_bytes(),
                maintype="application",
                subtype="pdf",
                filename=path.name,
            )

        with smtplib.SMTP(self.host, self.port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            login_username = self.username if "@" in self.username else self.from_email
            smtp.login(login_username, self.password)
            smtp.send_message(message)
        return EmailResult(True, "Email sent successfully.")
