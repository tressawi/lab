"""Configuration for DevAI."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JenkinsConfig:
    """Jenkins connection configuration."""
    url: str = ""
    username: str = ""
    api_token: str = ""
    default_job: str = ""
    verify_ssl: bool = True
    timeout_seconds: int = 600
    poll_interval_seconds: int = 10

    @classmethod
    def from_env(cls) -> "JenkinsConfig":
        """Load configuration from environment variables."""
        return cls(
            url=os.getenv("JENKINS_URL", ""),
            username=os.getenv("JENKINS_USERNAME", ""),
            api_token=os.getenv("JENKINS_API_TOKEN", ""),
            default_job=os.getenv("JENKINS_DEFAULT_JOB", ""),
            verify_ssl=os.getenv("JENKINS_VERIFY_SSL", "true").lower() == "true",
            timeout_seconds=int(os.getenv("JENKINS_TIMEOUT", "600")),
            poll_interval_seconds=int(os.getenv("JENKINS_POLL_INTERVAL", "10")),
        )


@dataclass
class ArtifactoryConfig:
    """Artifactory connection configuration."""
    url: str = ""
    username: str = ""
    api_key: str = ""
    default_repository: str = "libs-release-local"
    verify_ssl: bool = True
    timeout_seconds: int = 120

    @classmethod
    def from_env(cls) -> "ArtifactoryConfig":
        """Load configuration from environment variables."""
        return cls(
            url=os.getenv("ARTIFACTORY_URL", ""),
            username=os.getenv("ARTIFACTORY_USERNAME", ""),
            api_key=os.getenv("ARTIFACTORY_API_KEY", ""),
            default_repository=os.getenv("ARTIFACTORY_REPOSITORY", "libs-release-local"),
            verify_ssl=os.getenv("ARTIFACTORY_VERIFY_SSL", "true").lower() == "true",
            timeout_seconds=int(os.getenv("ARTIFACTORY_TIMEOUT", "120")),
        )


@dataclass
class DeploymentConfig:
    """Deployment environment configuration."""
    dev_auto_deploy: bool = True
    staging_auto_deploy: bool = False
    prod_requires_dual_approval: bool = True
    prod_approvers: list[str] = field(default_factory=list)
    rollback_window_hours: int = 24

    @classmethod
    def from_env(cls) -> "DeploymentConfig":
        """Load configuration from environment variables."""
        approvers = os.getenv("PROD_APPROVERS", "")
        return cls(
            dev_auto_deploy=os.getenv("DEV_AUTO_DEPLOY", "true").lower() == "true",
            staging_auto_deploy=os.getenv("STAGING_AUTO_DEPLOY", "false").lower() == "true",
            prod_requires_dual_approval=os.getenv("PROD_DUAL_APPROVAL", "true").lower() == "true",
            prod_approvers=approvers.split(",") if approvers else [],
            rollback_window_hours=int(os.getenv("ROLLBACK_WINDOW_HOURS", "24")),
        )


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

    # CI/CD configurations
    jenkins: Optional[JenkinsConfig] = None
    artifactory: Optional[ArtifactoryConfig] = None
    deployment: Optional[DeploymentConfig] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            store_path=os.getenv("DEVAI_STORE_PATH", "./context_store"),
            default_working_dir=os.getenv("DEVAI_WORKING_DIR", "."),
            default_agent=os.getenv("DEVAI_DEFAULT_AGENT", "dev"),
            audit_enabled=os.getenv("DEVAI_AUDIT_ENABLED", "true").lower() == "true",
            log_level=os.getenv("DEVAI_LOG_LEVEL", "INFO"),
            jenkins=JenkinsConfig.from_env(),
            artifactory=ArtifactoryConfig.from_env(),
            deployment=DeploymentConfig.from_env(),
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
