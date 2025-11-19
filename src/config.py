"""Configuration management for the bridge app."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud Configuration
    gcp_project_id: str
    gcp_location: str = "us-central1"
    agent_engine_resource_id: str
    
    # Optional: Google Cloud credentials path
    google_application_credentials: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Server Configuration
    port: int = 8000
    host: str = "0.0.0.0"
    
    # ADK Middleware Configuration
    app_name: str = "dojo_bridge"
    session_timeout_seconds: int = 1200
    execution_timeout_seconds: int = 600
    max_concurrent_executions: int = 10
    
    # Environment
    environment: str = "development"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def debug(self) -> bool:
        """Enable debug mode in development."""
        return not self.is_production


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

