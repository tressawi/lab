"""Configuration for DevAI."""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration."""

    # Context store location
    store_path: str = "./context_store"

    # Default working directory
    default_working_dir: str = "."

    # Agent settings
    default_agent: str = "dev"

    # Logging
    audit_enabled: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            store_path=os.getenv("DEVAI_STORE_PATH", "./context_store"),
            default_working_dir=os.getenv("DEVAI_WORKING_DIR", "."),
            default_agent=os.getenv("DEVAI_DEFAULT_AGENT", "dev"),
            audit_enabled=os.getenv("DEVAI_AUDIT_ENABLED", "true").lower() == "true",
            log_level=os.getenv("DEVAI_LOG_LEVEL", "INFO"),
        )

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from a JSON file."""
        import json

        config_path = Path(path)
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return cls(**data)

        return cls()


# Global config instance
config = Config.from_env()
