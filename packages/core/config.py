"""Application configuration using pydantic-settings."""

import re
import warnings
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Airport"
    debug: bool = False
    environment: str = "development"  # development, staging, production

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/airport"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage (S3-compatible)
    storage_bucket: str = "airport-documents"
    storage_endpoint: str | None = None  # For MinIO in dev
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Auth
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Password requirements
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = False

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_timeout_seconds: int = 120

    # Email (for notifications)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    from_email: str = "noreply@airport.app"

    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    cors_allow_credentials: bool = True

    # Frontend URLs (for emails)
    frontend_url: str = "http://localhost:3000"
    password_reset_url: str = ""  # Defaults to {frontend_url}/reset-password

    # Agent Configuration
    agent_timeout_seconds: int = 300
    extraction_confidence_threshold: float = 0.85
    require_human_review_below: float = 0.70

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_auth_requests: int = 5
    rate_limit_auth_window_seconds: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.environment == "production":
            # Secret key must be changed in production
            if self.secret_key == "change-me-in-production":
                raise ValueError(
                    "CRITICAL: SECRET_KEY must be set to a secure value in production. "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            # Secret key should be at least 32 characters
            if len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production"
                )
            # Anthropic API key should be set
            if not self.anthropic_api_key:
                warnings.warn(
                    "ANTHROPIC_API_KEY not set - AI extraction will not work",
                    RuntimeWarning,
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def password_reset_full_url(self) -> str:
        """Get full password reset URL."""
        if self.password_reset_url:
            return self.password_reset_url
        return f"{self.frontend_url}/reset-password"

    def validate_password(self, password: str) -> tuple[bool, str]:
        """
        Validate password meets security requirements.

        Returns (is_valid, error_message).
        """
        if len(password) < self.password_min_length:
            return False, f"Password must be at least {self.password_min_length} characters"

        if self.password_require_uppercase and not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if self.password_require_lowercase and not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if self.password_require_digit and not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        if self.password_require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"

        return True, ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
