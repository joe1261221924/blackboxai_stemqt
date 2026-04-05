"""
STEMQuest — Configuration
=========================
All settings are driven by environment variables so the same container image
runs in development, staging, and production without code changes.

Redis DB layout
---------------
  0  application cache + RQ job queue  (API process and worker share this)
  1  Flask-Limiter rate-limit counters  (isolated so eviction never resets counts)
  9  test isolation (never used in production)
"""
from __future__ import annotations

import os
from datetime import timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing or invalid."""


# ---------------------------------------------------------------------------
# Base config
# ---------------------------------------------------------------------------

class Config:

    # -- Flask ---------------------------------------------------------------
    SECRET_KEY: str  = _env("SECRET_KEY", "dev-secret-change-in-production-min32")
    DEBUG:      bool = _env_bool("FLASK_DEBUG", False)
    TESTING:    bool = False

    # -- SQLAlchemy / PostgreSQL ---------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = _env(
        "DATABASE_URL",
        "postgresql://stemquest:stemquest@localhost:5432/stemquest",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping":  True,
        "pool_recycle":   1800,
        "pool_size":      5,
        "max_overflow":   10,
        "pool_timeout":   30,
        "connect_args":   {"application_name": "stemquest-api"},
    }

    # -- Redis ---------------------------------------------------------------
    REDIS_URL: str = _env("REDIS_URL", "redis://localhost:6379/0")

    # -- JWT -----------------------------------------------------------------
    JWT_SECRET_KEY: str          = _env("JWT_SECRET_KEY", "dev-jwt-secret-change-in-prod-min32")
    JWT_TOKEN_LOCATION: list     = ["cookies", "headers"]
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(
        hours=_env_int("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24)
    )
    JWT_COOKIE_SECURE:       bool = _env_bool("JWT_COOKIE_SECURE", False)
    JWT_COOKIE_SAMESITE:     str  = _env("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT: bool = False
    JWT_ACCESS_COOKIE_NAME:  str  = "sq_access_token"
    JWT_HEADER_NAME:         str  = "Authorization"
    JWT_HEADER_TYPE:         str  = "Bearer"

    # -- CORS ----------------------------------------------------------------
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in _env("CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]

    # -- Flask-Limiter (Redis-backed) ----------------------------------------
    RATELIMIT_STORAGE_URI:     str  = _env("RATELIMIT_STORAGE_URL", "redis://localhost:6379/1")
    RATELIMIT_DEFAULT:         str  = "200 per hour"
    RATELIMIT_HEADERS_ENABLED: bool = True
    RATELIMIT_SWALLOW_ERRORS:  bool = True

    # -- PayPal --------------------------------------------------------------
    PAYPAL_CLIENT_ID:     str  = _env("PAYPAL_CLIENT_ID",     "")
    PAYPAL_CLIENT_SECRET: str  = _env("PAYPAL_CLIENT_SECRET", "")
    PAYPAL_BASE_URL:      str  = _env("PAYPAL_BASE_URL",      "https://api-m.sandbox.paypal.com")
    PAYPAL_WEBHOOK_ID:    str  = _env("PAYPAL_WEBHOOK_ID",    "")
    PAYPAL_DEMO_MODE:     bool = _env_bool("PAYPAL_DEMO_MODE", True)

    # -- Redis cache TTLs ----------------------------------------------------
    GAMI_SUMMARY_TTL:     int = _env_int("GAMI_SUMMARY_TTL",     60)   # seconds
    GAMI_LEADERBOARD_TTL: int = _env_int("GAMI_LEADERBOARD_TTL", 120)  # seconds

    # -- Validation ----------------------------------------------------------
    @classmethod
    def validate(cls) -> None:
        """Called during app-factory startup. Raises ConfigError on bad config."""
        if cls.DEBUG or cls.TESTING:
            return

        errors: list[str] = []

        if len(cls.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")
        if "dev-secret" in cls.SECRET_KEY:
            errors.append("SECRET_KEY still contains placeholder value — set a real secret")

        if len(cls.JWT_SECRET_KEY) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters long")
        if "dev-jwt" in cls.JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY still contains placeholder value — set a real secret")

        if not cls.JWT_COOKIE_SECURE:
            errors.append("JWT_COOKIE_SECURE=false in production — set true when serving HTTPS")

        if not cls.PAYPAL_DEMO_MODE:
            if not cls.PAYPAL_CLIENT_ID:
                errors.append("PAYPAL_CLIENT_ID is required when PAYPAL_DEMO_MODE=false")
            if not cls.PAYPAL_CLIENT_SECRET:
                errors.append("PAYPAL_CLIENT_SECRET is required when PAYPAL_DEMO_MODE=false")

        if errors:
            raise ConfigError(
                "Configuration errors — fix before deploying:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )


# ---------------------------------------------------------------------------
# Testing config
# ---------------------------------------------------------------------------

class TestingConfig(Config):
    TESTING: bool = True
    DEBUG:   bool = True

    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "connect_args":  {"check_same_thread": False},
    }

    JWT_COOKIE_SECURE:   bool = False
    PAYPAL_DEMO_MODE:    bool = True
    RATELIMIT_ENABLED:   bool = False
    RATELIMIT_STORAGE_URI: str = "memory://"

    REDIS_URL: str = _env("TEST_REDIS_URL", "redis://localhost:6379/9")

    GAMI_SUMMARY_TTL:     int = 0
    GAMI_LEADERBOARD_TTL: int = 0


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_CONFIGS: dict[str, type[Config]] = {
    "development": Config,
    "testing":     TestingConfig,
    "production":  Config,
}


def get_config(env: str | None = None) -> type[Config]:
    env = env or _env("FLASK_ENV", "development")
    return _CONFIGS.get(env, Config)
