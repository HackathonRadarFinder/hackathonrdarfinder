
from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_driver(cls, value):
        if isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value[len(prefix):]
        return value

    # Authentication
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,
        le=120,
    )

    # Application
    APP_NAME: str = "Hackathon Radar AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Logging
    LOG_LEVEL: str = "INFO"

    EMAIL_MODE: Literal["disabled", "dry-run", "enabled"] = "disabled"
    SMTP_HOST: str = Field(default="", max_length=255)
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_TLS: Literal["starttls", "implicit"] = "starttls"
    SMTP_TIMEOUT: float = Field(default=10, gt=0, le=60)
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    EMAIL_FROM: EmailStr = "noreply@example.com"

    @field_validator("EMAIL_FROM", mode="before")
    @classmethod
    def validate_sender_header(cls, value):
        if isinstance(value, str) and any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Invalid sender header")
        return value

    @model_validator(mode="after")
    def validate_email_config(self):
        if any(ord(c) <= 32 or ord(c) == 127 for c in self.SMTP_HOST):
            raise ValueError("Invalid SMTP host")
        if any(ord(c) < 32 for c in self.SMTP_USERNAME):
            raise ValueError("Invalid SMTP configuration")
        if bool(self.SMTP_USERNAME) != bool(self.SMTP_PASSWORD.get_secret_value()):
            raise ValueError("SMTP username and password must be configured together")
        if self.EMAIL_MODE == "enabled" and not self.SMTP_HOST.strip():
            raise ValueError("Enabled email requires SMTP_HOST")
        return self

    model_config = SettingsConfigDict(
        hide_input_in_errors=True,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
