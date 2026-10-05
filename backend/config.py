"""Backend configuration management."""
import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "Quantum Kavach"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # Database
    database_url: str = "sqlite:///./quantum_kavach.db"
    database_echo: bool = False

    # Quantum
    default_shots: int = 2000
    min_shots: int = 100
    max_shots: int = 100000
    default_seed: int | None = None
    qiskit_backend: str = "qasm_simulator"

    # Detection
    default_threshold: float = 0.15
    min_threshold: float = 0.0
    max_threshold: float = 1.0
    statistical_method: Literal["chi_square", "tv_distance", "both"] = "tv_distance"
    significance_level: float = 0.05

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Security
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


settings = get_settings()
