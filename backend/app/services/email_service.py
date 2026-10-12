"""Safe rendering and explicit SMTP outcomes; acceptance is not delivery."""
from email.message import EmailMessage
from pathlib import Path
import smtplib
import ssl
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import EmailStr, HttpUrl, TypeAdapter

from app.core.config import Settings

templates = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates" / "emails"),
    autoescape=select_autoescape(["html"]), undefined=StrictUndefined,
)


def render_message(config: Settings, recipient: str, name: str, title: str,
                   kind: str, event_at: str, url: str) -> EmailMessage:
    if any(ord(c) < 32 or ord(c) == 127 for c in recipient + title + str(config.EMAIL_FROM)):
        raise ValueError("Invalid email header")
    recipient = str(TypeAdapter(EmailStr).validate_python(recipient))
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError("Invalid event link")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Invalid event link")
    TypeAdapter(HttpUrl).validate_python(url)
    if kind not in ("registration", "upcoming"):
        raise ValueError("Invalid reminder kind")
    html = templates.get_template(f"{kind}_reminder.html").render(
        user_name=name, hackathon_name=title, event_at=event_at, hackathon_url=url,
    )
    message = EmailMessage()
    message["From"] = str(config.EMAIL_FROM)
    message["To"] = recipient
    message["Subject"] = f"Reminder: {title}"
    message.set_content(f"{title}: {event_at}\n{url}")
    message.add_alternative(html, subtype="html")
    return message


def send_message(config: Settings, message: EmailMessage) -> str:
    if config.EMAIL_MODE != "enabled":
        return config.EMAIL_MODE
    context = ssl.create_default_context()
    outcome = None
    sending = False
    try:
        factory = smtplib.SMTP_SSL if config.SMTP_TLS == "implicit" else smtplib.SMTP
        kwargs = {"timeout": config.SMTP_TIMEOUT}
        if config.SMTP_TLS == "implicit":
            kwargs["context"] = context
        with factory(config.SMTP_HOST, config.SMTP_PORT, **kwargs) as server:
            server.ehlo()
            if config.SMTP_TLS == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if config.SMTP_USERNAME:
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD.get_secret_value())
            sending = True
            outcome = "refused" if server.send_message(message) else "accepted"
        return outcome
    except smtplib.SMTPRecipientsRefused:
        return "refused"
    except smtplib.SMTPServerDisconnected:
        return outcome or ("unknown" if sending else "transport_error")
    except smtplib.SMTPException as error:
        # A negative SMTP response is a known rejection. Other errors during
        # DATA may follow acceptance; do not automatically retry uncertain sends.
        return outcome or ("unknown" if sending and not isinstance(error, smtplib.SMTPResponseException) else "transport_error")
    except (TimeoutError, OSError):
        return outcome or ("unknown" if sending else "transport_error")
