"""Email OTP recovery with per-account cooldown, bounded guesses and session revocation."""
from datetime import datetime, timedelta, timezone
import httpx
import hashlib
import hmac
import logging
import secrets

from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.core import AuditLog, User
from app.models.password_reset_otp import PasswordResetOTP

logger = logging.getLogger(__name__)
GENERIC_RESPONSE = 'If an active account exists, a password reset code will be emailed.'
INVALID_RESPONSE = 'Invalid or expired reset code.'
CODE_LIFETIME = timedelta(minutes=10)
COOLDOWN = timedelta(seconds=60)
WINDOW = timedelta(hours=1)
MAX_SENDS = 3
MAX_ATTEMPTS = 5


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode('utf-8'),
                    ('password-reset-otp-v1:' + value).encode('utf-8'), hashlib.sha256).hexdigest()


def address_key(email: str) -> str:
    return digest('address:' + email.strip().lower())


def code_digest(email: str, code: str) -> str:
    return digest('code:' + email.strip().lower() + ':' + code)


def send_otp(email: str, code: str) -> bool:
    """HTTPS transactional email; no SMTP dependency or OTPs in server logs."""
    if not settings.PASSWORD_RESET_OTP_ENABLED:
        return False
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            response = client.post(
                'https://api.resend.com/emails',
                headers={
                    'Authorization': 'Bearer ' + settings.RESEND_API_KEY.get_secret_value(),
                    'Content-Type': 'application/json',
                    'User-Agent': 'HackathonRadarFinder/1.0',
                },
                json={
                    'from': str(settings.EMAIL_FROM),
                    'to': [email],
                    'subject': 'Hackathon Radar Finder password reset code',
                    'text': (
                        'Your Hackathon Radar Finder password reset code is: ' + code +
                        '\\nThis code expires in 10 minutes. If you did not request it, ignore this email.'
                    ),
                },
            )
        # Do not log response bodies: provider errors may contain recipient info.
        return response.status_code == 200
    except (httpx.HTTPError, ValueError):
        return False

def request_otp(email: str, db) -> dict:
    if not settings.PASSWORD_RESET_OTP_ENABLED:
        raise HTTPException(503, 'Email password reset is not configured.')
    email = email.strip().lower()
    now = utcnow()
    row = db.scalar(select(PasswordResetOTP)
                    .where(PasswordResetOTP.email_key == address_key(email)).with_for_update())
    user = db.scalar(select(User).where(User.email == email, User.status == 'active'))
    if user is None:
        return {'message': GENERIC_RESPONSE}
    if row is not None:
        if now - row.sent_at < COOLDOWN:
            return {'message': GENERIC_RESPONSE}
        if now - row.window_started_at < WINDOW and row.requests_in_window >= MAX_SENDS:
            return {'message': GENERIC_RESPONSE}
    code = f'{secrets.randbelow(1_000_000):06d}'
    # Send before persisting; unsuccessful delivery never produces a valid code.
    if not send_otp(email, code):
        logger.warning('Password reset SMTP delivery was not accepted; no code activated')
        return {'message': GENERIC_RESPONSE}
    if row is None:
        row = PasswordResetOTP(email_key=address_key(email), code_digest=code_digest(email, code),
            sent_at=now, expires_at=now + CODE_LIFETIME, attempts=0,
            window_started_at=now, requests_in_window=1)
        db.add(row)
    else:
        if now - row.window_started_at >= WINDOW:
            row.window_started_at = now
            row.requests_in_window = 0
        row.requests_in_window += 1
        row.code_digest = code_digest(email, code)
        row.sent_at = now
        row.expires_at = now + CODE_LIFETIME
        row.attempts = 0
    db.commit()
    return {'message': GENERIC_RESPONSE}


def confirm_otp(email: str, code: str, new_password: str, db) -> dict:
    if not settings.PASSWORD_RESET_OTP_ENABLED:
        raise HTTPException(503, 'Email password reset is not configured.')
    email = email.strip().lower()
    row = db.scalar(select(PasswordResetOTP)
                    .where(PasswordResetOTP.email_key == address_key(email)).with_for_update())
    now = utcnow()
    if row is None or row.expires_at <= now or row.attempts >= MAX_ATTEMPTS:
        raise HTTPException(400, INVALID_RESPONSE)
    if not hmac.compare_digest(row.code_digest, code_digest(email, code)):
        row.attempts += 1
        db.commit()
        raise HTTPException(400, INVALID_RESPONSE)
    user = db.scalar(select(User).where(User.email == email, User.status == 'active').with_for_update())
    if user is None:
        raise HTTPException(400, INVALID_RESPONSE)
    user.password_hash = get_password_hash(new_password)
    user.token_version = (user.token_version or 0) + 1
    db.add(AuditLog(user_id=user.id, action='password_reset_completed',
                    entity_type='user', entity_id=user.id, details='{}'))
    db.delete(row)  # Single use; code cannot be replayed.
    db.commit()
    return {'message': 'Password updated. Please sign in with your new password.'}
