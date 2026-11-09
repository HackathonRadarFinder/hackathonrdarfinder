"""Single active, time-limited email OTP per account address; never store plaintext OTPs."""
from sqlalchemy import Column, DateTime, Integer, String
from app.core.database import Base


class PasswordResetOTP(Base):
    __tablename__ = 'password_reset_otps'

    # HMAC of normalized email; prevents a second email-address directory.
    email_key = Column(String(64), primary_key=True)
    code_digest = Column(String(64), nullable=False)
    sent_at = Column(DateTime(), nullable=False)
    expires_at = Column(DateTime(), nullable=False)
    attempts = Column(Integer(), nullable=False, default=0)
    window_started_at = Column(DateTime(), nullable=False)
    requests_in_window = Column(Integer(), nullable=False, default=1)
