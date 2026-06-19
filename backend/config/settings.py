from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator, AnyHttpUrl, EmailStr
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
    SLOWAPI_REDIS_URL: Optional[str] = Field(None, env="SLOWAPI_REDIS_URL")
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_CAR_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_CAR_PER_MINUTE")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if not v:
            return []
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("ENVIRONMENT")
    def validate_environment(cls, v):
        allowed = ("dev", "staging", "prod", "testing")
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(allowed)}")
        return v

    @field_validator("DATABASE_URL", "REDIS_URL", "JWT_SECRET", mode="before")
    def check_required_fields(cls, v, info):
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} is required")
        return v

    @model_validator(mode="after")
    def check_prod_config(self):
        if self.ENVIRONMENT == "prod":
            if not self.JWT_SECRET or self.JWT_SECRET in ("changeme", "secret", "a1b2c3d4e5f6"):
                raise ValueError("JWT_SECRET must be a strong random secret in production")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must be set in production")
        return self


settings = Settings()
