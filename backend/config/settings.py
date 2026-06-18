from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, AnyHttpUrl, EmailStr
from typing import Optional, List
import os
import json


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    LM_STUDIO_URL: Optional[AnyHttpUrl] = Field(None, env="LM_STUDIO_URL")
    DEFAULT_LLM_MODEL: str = Field(default="llama3.1:8b", env="DEFAULT_LLM_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.3, env="LLM_TEMPERATURE")
    LLM_TIMEOUT: int = Field(default=120, env="LLM_TIMEOUT")
    MQTT_URL: str = Field(default="mqtt://localhost:1883", env="MQTT_URL")
    MQTT_USERNAME: Optional[str] = Field(None, env="MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = Field(None, env="MQTT_PASSWORD")
    CORS_ORIGINS: Optional[List[str]] = Field(default=[], env="CORS_ORIGINS")
    ENVIRONMENT: str = Field(default="dev", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=40, env="DB_MAX_OVERFLOW")
    MQTT_URL: str = Field(default="mqtt://localhost:1883", env="MQTT_URL")
    MQTT_USERNAME: Optional[str] = Field(None, env="MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = Field(None, env="MQTT_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or JSON array."""
        if not v:
            return []
        if isinstance(v, list):
            return v
        # Try to parse as JSON first
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            pass
        # Fall back to comma-separated
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("ENVIRONMENT")
    def validate_environment(cls, v, info):
        allowed = ("dev", "staging", "prod", "testing")
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(allowed)}")
        return v

    @field_validator("DATABASE_URL", "REDIS_URL", "JWT_SECRET", mode="before")
    def check_required_fields(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} is required")
        return v


settings = Settings()
