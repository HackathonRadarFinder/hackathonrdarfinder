import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)

# Locate templates directory relative to this file
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

class EmailService:
    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        """Sends an HTML email. Returns True on success, False on failure without crashing."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        # Skip actual network dispatch in testing or unconfigured local environments
        if not settings.SMTP_USERNAME or settings.SMTP_HOST in ("localhost", "test_smtp"):
            logger.info("Mock Email Sent: Subject='%s' To='%s'", subject, to_email)
            return True

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Email delivered successfully to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e), exc_info=True)
            return False

    @classmethod
    def send_registration_reminder(
        cls, to_email: str, user_name: str, hackathon_name: str, deadline: str, hackathon_url: str
    ) -> bool:
        template = jinja_env.get_template("registration_reminder.html")
        html = template.render(
            user_name=user_name,
            hackathon_name=hackathon_name,
            deadline=deadline,
            hackathon_url=hackathon_url
        )
        subject = f"Reminder: Registration closing soon for {hackathon_name}"
        return cls._send_email(to_email, subject, html)

    @classmethod
    def send_hackathon_reminder(
        cls, to_email: str, user_name: str, hackathon_name: str, start_date: str, hackathon_url: str
    ) -> bool:
        template = jinja_env.get_template("hackathon_reminder.html")
        html = template.render(
            user_name=user_name,
            hackathon_name=hackathon_name,
            start_date=start_date,
            hackathon_url=hackathon_url
        )
        subject = f"Upcoming: {hackathon_name} starts soon!"
        return cls._send_email(to_email, subject, html)