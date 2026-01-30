"""
Application Configuration
Loads settings from environment variables and AWS Secrets Manager
"""
import json
from functools import lru_cache
from typing import Optional

import boto3
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Application
    app_name: str = Field(default="Sentinel", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")

    # AWS
    aws_region: str = Field(default="eu-west-2", alias="AWS_REGION")
    aws_account_id: str = Field(default="108101918328", alias="AWS_ACCOUNT_ID")

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")

    # Secrets Manager
    rds_secret_name: str = Field(alias="RDS_SECRET_NAME")
    redis_secret_name: str = Field(alias="REDIS_SECRET_NAME")
    jwt_secret_name: str = Field(alias="JWT_SECRET_NAME")
    xero_secret_name: str = Field(alias="XERO_SECRET_NAME")
    twilio_secret_name: str = Field(alias="TWILIO_SECRET_NAME")
    sendgrid_secret_name: str = Field(alias="SENDGRID_SECRET_NAME")

    # JWT
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Magic Link
    magic_link_expire_minutes: int = Field(default=15, alias="MAGIC_LINK_EXPIRE_MINUTES")
    magic_link_base_url: str = Field(default="http://localhost:3000", alias="MAGIC_LINK_BASE_URL")

    # Xero
    xero_client_id: Optional[str] = Field(default=None, alias="XERO_CLIENT_ID")
    xero_client_secret: Optional[str] = Field(default=None, alias="XERO_CLIENT_SECRET")
    xero_redirect_uri: Optional[str] = Field(default=None, alias="XERO_REDIRECT_URI")
    xero_scopes: str = Field(default="accounting.transactions accounting.contacts accounting.attachments offline_access", alias="XERO_SCOPES")
    xero_sync_interval_minutes: int = Field(default=60, alias="XERO_SYNC_INTERVAL_MINUTES")
    xero_rate_limit_per_minute: int = Field(default=60, alias="XERO_RATE_LIMIT_PER_MINUTE")

    # Twilio
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(default=None, alias="TWILIO_PHONE_NUMBER")
    twilio_whatsapp_number: Optional[str] = Field(default=None, alias="TWILIO_WHATSAPP_NUMBER")

    # SendGrid
    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")
    sendgrid_from_email: str = Field(default="noreply@sentinel.com", alias="SENDGRID_FROM_EMAIL")
    sendgrid_from_name: str = Field(default="Sentinel", alias="SENDGRID_FROM_NAME")

    # S3
    s3_bucket_name: str = Field(default="sentinel-documents-prod", alias="S3_BUCKET_NAME")
    s3_region: str = Field(default="eu-west-2", alias="S3_REGION")
    s3_presigned_url_expiry: int = Field(default=3600, alias="S3_PRESIGNED_URL_EXPIRY")

    # AWS Textract
    textract_region: str = Field(default="eu-west-2", alias="TEXTRACT_REGION")

    # Celery
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")

    # Chase Settings
    chase_default_frequency_days: int = Field(default=7, alias="CHASE_DEFAULT_FREQUENCY_DAYS")
    chase_default_escalation_days: int = Field(default=14, alias="CHASE_DEFAULT_ESCALATION_DAYS")
    chase_max_retry_attempts: int = Field(default=3, alias="CHASE_MAX_RETRY_ATTEMPTS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000", alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")

    # Feature Flags
    feature_voice_ai_enabled: bool = Field(default=True, alias="FEATURE_VOICE_AI_ENABLED")
    feature_whatsapp_enabled: bool = Field(default=True, alias="FEATURE_WHATSAPP_ENABLED")
    feature_auto_exclusion_enabled: bool = Field(default=True, alias="FEATURE_AUTO_EXCLUSION_ENABLED")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list:
        """Parse comma-separated CORS origins"""
        return [origin.strip() for origin in v.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    @property
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.environment == "staging"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


class SecretsManager:
    """AWS Secrets Manager integration"""

    def __init__(self, region: str = "eu-west-2"):
        self.client = boto3.client("secretsmanager", region_name=region)
        self._cache = {}

    def get_secret(self, secret_name: str) -> dict:
        """Get secret from AWS Secrets Manager with caching"""
        if secret_name in self._cache:
            return self._cache[secret_name]

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_value = json.loads(response["SecretString"])
            self._cache[secret_name] = secret_value
            return secret_value
        except Exception as e:
            raise ValueError(f"Failed to retrieve secret '{secret_name}': {str(e)}")

    def get_database_credentials(self, secret_name: str) -> dict:
        """Get RDS credentials"""
        return self.get_secret(secret_name)

    def get_redis_credentials(self, secret_name: str) -> dict:
        """Get Redis credentials"""
        return self.get_secret(secret_name)

    def get_jwt_secret(self, secret_name: str) -> str:
        """Get JWT secret"""
        secret = self.get_secret(secret_name)
        return secret.get("secret", "")

    def get_xero_credentials(self, secret_name: str) -> dict:
        """Get Xero OAuth credentials"""
        return self.get_secret(secret_name)

    def get_twilio_credentials(self, secret_name: str) -> dict:
        """Get Twilio credentials"""
        return self.get_secret(secret_name)

    def get_sendgrid_credentials(self, secret_name: str) -> dict:
        """Get SendGrid credentials"""
        return self.get_secret(secret_name)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


@lru_cache
def get_secrets_manager() -> SecretsManager:
    """Get cached secrets manager instance"""
    settings = get_settings()
    return SecretsManager(region=settings.aws_region)


# Global settings instance
settings = get_settings()
secrets_manager = get_secrets_manager()
