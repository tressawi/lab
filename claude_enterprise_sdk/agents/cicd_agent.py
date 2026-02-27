"""CI/CD Agent - Jenkins build orchestration and Artifactory artifact management."""
from __future__ import annotations

from typing import Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .base import BaseAgent, AgentResult


class Environment(Enum):
    """Deployment environments."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


@dataclass
class DeploymentResult:
    """Result from a deployment operation."""
    environment: Environment
    artifact_version: str
    artifact_sha256: str
    success: bool
    approved_by: list[str]
    error: Optional[str] = None


CICD_SYSTEM_PROMPT = """You are a DevOps engineer and CI/CD specialist.

## Your Role
You are the CI/CD Agent in a multi-agent development system. Your job is to:
- Trigger and monitor Jenkins builds
- Upload artifacts to Artifactory with proper versioning
- Orchestrate deployments to different environments
- Maintain separation of duties (you do NOT write application code)

## Separation of Duties
CRITICAL: You are NOT allowed to:
- Modify source code files
- Create or edit application files
- Change business logic
- Write test files

You ARE allowed to:
- Read pipeline configurations and build files
- Trigger builds via Jenkins API
- Upload/download artifacts via Artifactory API
- Execute deployment commands (kubectl, docker, etc.)
- Monitor build and deployment status
- Read logs and configuration files

## Environment Progression
- dev: Auto-deploy on successful build (no approval required)
- staging: Requires test pass and single approval
- prod: Requires dual approval from two different approvers

## Compliance Requirements
- Log all build triggers with initiator identity
- Record artifact checksums (SHA-256) for every artifact
- Maintain deployment audit trail with approver chain
- Enforce approval gates for production deployments
- Support rollback to previous versions

## Output Format
When reporting results, always include:
1. Build status and number
2. Artifact details (path, version, checksum)
3. Deployment target and status
4. Audit trail entries created

## Error Handling
- If a build fails, report the failure and console log URL
- If an artifact upload fails, retry once before failing
- If a deployment fails, do NOT retry automatically - require human intervention
- Never skip security gates or approval requirements
"""


class CICDAgent(BaseAgent):
    """
    CI/CD Agent for Jenkins builds and Artifactory artifact management.

    Enforces separation of duties: this agent cannot modify application code,
    only trigger builds and manage deployments.

    Tool restrictions:
    - NO Write tool (cannot create files)
    - NO Edit tool (cannot modify files)
    - Read only for configuration files
    - Bash for CI/CD commands only
    """

    # Read-only tools - no Write/Edit to enforce separation of duties
    DEFAULT_TOOLS = [
        "Read",      # Read configs and build files only
        "Bash",      # Execute CI/CD commands (not code edits)
        "Glob",      # Find configuration files
        "Grep",      # Search configurations
    ]

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        store_path: str = "./context_store",
        jenkins_config: Optional[dict] = None,
        artifactory_config: Optional[dict] = None
    ):
        """
        Initialize the CI/CD Agent.

        Args:
            system_prompt: Custom system prompt (uses default if not provided)
            allowed_tools: Custom tool list (uses DEFAULT_TOOLS if not provided)
            store_path: Path to the context store
            jenkins_config: Jenkins configuration dict
            artifactory_config: Artifactory configuration dict
        """
        super().__init__(
            name="cicd",
            system_prompt=system_prompt or CICD_SYSTEM_PROMPT,
            allowed_tools=allowed_tools or self.DEFAULT_TOOLS,
            store_path=store_path
        )
        self.jenkins_config = jenkins_config or {}
        self.artifactory_config = artifactory_config or {}

    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[dict] = None,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        pipeline_id: Optional[str] = None
    ) -> AgentResult:
        """
        Trigger a Jenkins build and wait for completion.

        Args:
            job_name: Name of the Jenkins job to trigger
            parameters: Optional build parameters
            working_dir: Working directory
            task_id: Task ID for tracking
            pipeline_id: Pipeline ID for correlation

        Returns:
            AgentResult with build status and details
        """
        from ..integrations.jenkins import JenkinsClient, JenkinsConfig
        from .utilities.audit import log_build_trigger

        # Create client from config
        config = JenkinsConfig(**self.jenkins_config) if self.jenkins_config else JenkinsConfig.from_env()
        client = JenkinsClient(config)

        try:
            # Build context for audit
            context = {
                "agent_name": self.name,
                "task_id": task_id,
                "pipeline_id": pipeline_id,
                "store_path": self.store_path,
            }

            # Trigger and wait for build
            build_info = await client.trigger_and_wait(job_name, parameters)

            # Log the build trigger
            await log_build_trigger(
                job_name=job_name,
                build_number=build_info.build_number,
                triggered_by=self.name,
                pipeline_id=pipeline_id or "",
                context=context
            )

            # Format result
            status_str = build_info.status.value
            duration_sec = build_info.duration_ms / 1000

            content = f"""Build completed:
- Job: {job_name}
- Build Number: {build_info.build_number}
- Status: {status_str}
- Duration: {duration_sec:.1f}s
- Console: {build_info.console_url}
- Artifacts: {len(build_info.artifacts)}"""

            return AgentResult(
                task_id=task_id or f"cicd-build-{build_info.build_number}",
                session_id=None,
                content=content,
                success=status_str == "SUCCESS",
                error=None if status_str == "SUCCESS" else f"Build {status_str}"
            )

        except Exception as e:
            return AgentResult(
                task_id=task_id or "cicd-build-error",
                session_id=None,
                content="",
                success=False,
                error=str(e)
            )

        finally:
            await client.close()

    async def upload_artifact(
        self,
        artifact_path: str,
        repository: Optional[str] = None,
        target_path: str = "",
        version: str = "",
        working_dir: str = ".",
        task_id: Optional[str] = None,
        pipeline_id: Optional[str] = None
    ) -> AgentResult:
        """
        Upload an artifact to Artifactory.

        Args:
            artifact_path: Local path to the artifact
            repository: Artifactory repository name
            target_path: Target path in the repository
            version: Version string for the artifact
            working_dir: Working directory
            task_id: Task ID for tracking
            pipeline_id: Pipeline ID for correlation

        Returns:
            AgentResult with upload details including checksums
        """
        from ..integrations.artifactory import ArtifactoryClient, ArtifactoryConfig
        from .utilities.audit import log_artifact_upload

        # Create client from config
        config = ArtifactoryConfig(**self.artifactory_config) if self.artifactory_config else ArtifactoryConfig.from_env()
        client = ArtifactoryClient(config)

        try:
            # Build context for audit
            context = {
                "agent_name": self.name,
                "task_id": task_id,
                "pipeline_id": pipeline_id,
                "store_path": self.store_path,
            }

            # Upload artifact
            local_path = Path(artifact_path)
            properties = {"version": version} if version else None

            metadata = await client.upload_artifact(
                local_path=local_path,
                repository=repository,
                target_path=target_path,
                properties=properties
            )

            # Log the upload
            await log_artifact_upload(
                artifact_path=metadata.path,
                repository=metadata.repository,
                version=version,
                sha256=metadata.sha256,
                uploaded_by=self.name,
                pipeline_id=pipeline_id or "",
                context=context
            )

            content = f"""Artifact uploaded:
- Repository: {metadata.repository}
- Path: {metadata.path}
- Version: {version}
- Size: {metadata.size_bytes} bytes
- SHA-256: {metadata.sha256}
- MD5: {metadata.md5}
- Download URL: {metadata.download_uri}"""

            return AgentResult(
                task_id=task_id or f"cicd-upload-{version}",
                session_id=None,
                content=content,
                success=True,
                error=None
            )

        except Exception as e:
            return AgentResult(
                task_id=task_id or "cicd-upload-error",
                session_id=None,
                content="",
                success=False,
                error=str(e)
            )

        finally:
            await client.close()

    async def deploy(
        self,
        environment: Environment,
        artifact_version: str,
        artifact_sha256: str = "",
        working_dir: str = ".",
        task_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        approved_by: Optional[list[str]] = None
    ) -> AgentResult:
        """
        Deploy an artifact to a target environment.

        Args:
            environment: Target environment (dev, staging, prod)
            artifact_version: Version of the artifact to deploy
            artifact_sha256: SHA-256 checksum for verification
            working_dir: Working directory
            task_id: Task ID for tracking
            pipeline_id: Pipeline ID for correlation
            approved_by: List of approvers (required for staging/prod)

        Returns:
            AgentResult with deployment status
        """
        from .utilities.audit import log_deployment

        # Build context for audit
        context = {
            "agent_name": self.name,
            "task_id": task_id,
            "pipeline_id": pipeline_id,
            "store_path": self.store_path,
        }

        # Validate approval requirements
        approved_by = approved_by or []
        if environment == Environment.STAGING and len(approved_by) < 1:
            return AgentResult(
                task_id=task_id or "cicd-deploy-error",
                session_id=None,
                content="",
                success=False,
                error="Staging deployment requires at least one approval"
            )

        if environment == Environment.PROD and len(approved_by) < 2:
            return AgentResult(
                task_id=task_id or "cicd-deploy-error",
                session_id=None,
                content="",
                success=False,
                error="Production deployment requires dual approval (two different approvers)"
            )

        if environment == Environment.PROD and len(set(approved_by)) < 2:
            return AgentResult(
                task_id=task_id or "cicd-deploy-error",
                session_id=None,
                content="",
                success=False,
                error="Production deployment requires two DIFFERENT approvers"
            )

        try:
            # In a real implementation, this would:
            # 1. Download artifact from Artifactory
            # 2. Verify checksum
            # 3. Execute deployment (kubectl, docker, etc.)
            # 4. Verify deployment health

            # For now, use the agent's AI capabilities to reason about deployment
            deployment_task = f"""Deploy artifact version {artifact_version} to {environment.value}.

Environment: {environment.value}
Artifact Version: {artifact_version}
Artifact SHA-256: {artifact_sha256}
Approved By: {', '.join(approved_by) if approved_by else 'N/A (dev environment)'}

Execute the appropriate deployment commands for this environment.
Verify the deployment was successful."""

            result = await self.run(
                task=deployment_task,
                working_dir=working_dir,
                task_id=task_id
            )

            # Log the deployment
            await log_deployment(
                environment=environment.value,
                artifact_version=artifact_version,
                deployed_by=self.name,
                approved_by=approved_by,
                pipeline_id=pipeline_id or "",
                status="success" if result.success else "failed",
                context=context
            )

            return result

        except Exception as e:
            # Log failed deployment
            await log_deployment(
                environment=environment.value,
                artifact_version=artifact_version,
                deployed_by=self.name,
                approved_by=approved_by,
                pipeline_id=pipeline_id or "",
                status="failed",
                context=context
            )

            return AgentResult(
                task_id=task_id or "cicd-deploy-error",
                session_id=None,
                content="",
                success=False,
                error=str(e)
            )

    async def rollback(
        self,
        environment: Environment,
        target_version: str,
        reason: str,
        approved_by: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        pipeline_id: Optional[str] = None
    ) -> AgentResult:
        """
        Rollback to a previous artifact version.

        Args:
            environment: Target environment
            target_version: Version to rollback to
            reason: Reason for rollback
            approved_by: Approver for the rollback
            working_dir: Working directory
            task_id: Task ID for tracking
            pipeline_id: Pipeline ID for correlation

        Returns:
            AgentResult with rollback status
        """
        from .utilities.audit import log_rollback

        # Build context for audit
        context = {
            "agent_name": self.name,
            "task_id": task_id,
            "pipeline_id": pipeline_id,
            "store_path": self.store_path,
        }

        try:
            # Execute rollback using agent's AI capabilities
            rollback_task = f"""Rollback {environment.value} to version {target_version}.

Environment: {environment.value}
Target Version: {target_version}
Reason: {reason}
Approved By: {approved_by}

Execute the rollback procedure:
1. Download the previous artifact version from Artifactory
2. Deploy the previous version
3. Verify the rollback was successful
4. Report the status"""

            result = await self.run(
                task=rollback_task,
                working_dir=working_dir,
                task_id=task_id
            )

            # Log the rollback
            await log_rollback(
                environment=environment.value,
                from_version="current",
                to_version=target_version,
                reason=reason,
                initiated_by=self.name,
                approved_by=approved_by,
                context=context
            )

            return result

        except Exception as e:
            return AgentResult(
                task_id=task_id or "cicd-rollback-error",
                session_id=None,
                content="",
                success=False,
                error=str(e)
            )

    async def get_deployment_status(
        self,
        environment: Environment,
        working_dir: str = "."
    ) -> AgentResult:
        """
        Check the current deployment status of an environment.

        Args:
            environment: Environment to check
            working_dir: Working directory

        Returns:
            AgentResult with current deployment status
        """
        status_task = f"""Check the deployment status of the {environment.value} environment.

Report:
1. Currently deployed version
2. Deployment timestamp
3. Health status
4. Any active alerts or issues"""

        return await self.run(
            task=status_task,
            working_dir=working_dir,
            task_id=f"cicd-status-{environment.value}"
        )
