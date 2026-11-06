"""
Stage 25 – Optional E-mail Notifier
Sends alert messages via SMTP.
Silently skipped if email config is not provided in settings.
"""

import smtplib
from email.mime.text import MIMEText
from datetime import datetime


class EmailNotifier:
    """
    Sends email alerts via SMTP.

    Parameters
    ----------
    smtp_host     : str  – SMTP server hostname
    smtp_port     : int  – port (default 587 for TLS)
    sender        : str  – from address
    recipients    : list – to addresses
    username      : str  – login username
    password      : str  – login password
    use_tls       : bool – enable STARTTLS (default True)
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        sender: str = "",
        recipients: list = None,
        username: str = "",
        password: str = "",
        use_tls: bool = True
    ):
        self.smtp_host   = smtp_host
        self.smtp_port   = smtp_port
        self.sender      = sender
        self.recipients  = recipients or []
        self.username    = username
        self.password    = password
        self.use_tls     = use_tls

    def send(self, message: str, level: str = "INFO") -> bool:
        """
        Send *message* via email.
        Returns True if successful, False on failure (logs error, does not raise).
        """
        if not self.recipients:
            return False

        subject = f"[Indian Day Trader] {level.upper()} Alert"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"Time: {ts}\nLevel: {level.upper()}\n\n{message}"

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password)
                smtp.sendmail(self.sender, self.recipients, msg.as_string())
            return True
        except Exception as exc:   # noqa: BLE001
            print(f"[EmailNotifier] Failed to send email: {exc}")
            return False
