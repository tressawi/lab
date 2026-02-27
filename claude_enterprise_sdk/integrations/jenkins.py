"""Jenkins API integration for CI/CD operations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class BuildStatus(Enum):
    """Jenkins build status."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    UNSTABLE = "UNSTABLE"
    ABORTED = "ABORTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"


@dataclass
class JenkinsConfig:
    """Jenkins connection configuration."""
    url: str = ""
    username: str = ""
    api_token: str = ""
    verify_ssl: bool = True
    timeout_seconds: int = 600
    poll_interval_seconds: int = 10

    @classmethod
    def from_env(cls) -> "JenkinsConfig":
        """Load configuration from environment variables."""
        import os
        return cls(
            url=os.getenv("JENKINS_URL", ""),
            username=os.getenv("JENKINS_USERNAME", ""),
            api_token=os.getenv("JENKINS_API_TOKEN", ""),
            verify_ssl=os.getenv("JENKINS_VERIFY_SSL", "true").lower() == "true",
            timeout_seconds=int(os.getenv("JENKINS_TIMEOUT", "600")),
            poll_interval_seconds=int(os.getenv("JENKINS_POLL_INTERVAL", "10")),
        )


@dataclass
class JenkinsBuildInfo:
    """Information about a Jenkins build."""
    job_name: str
    build_number: int
    status: BuildStatus
    result: Optional[str] = None
    duration_ms: int = 0
    timestamp: Optional[datetime] = None
    url: str = ""
    artifacts: list[dict] = field(default_factory=list)
    test_results: Optional[dict] = None
    console_url: Optional[str] = None


class JenkinsClient:
    """
    Async client for Jenkins API operations.

    Provides methods to trigger builds, monitor status, and retrieve artifacts.
    """

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                auth = aiohttp.BasicAuth(
                    self.config.username,
                    self.config.api_token
                )
                connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl)
                self._session = aiohttp.ClientSession(
                    auth=auth,
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                )
            except ImportError:
                raise ImportError("aiohttp is required for Jenkins integration. Install with: pip install aiohttp")
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[dict] = None
    ) -> int:
        """
        Trigger a Jenkins build.

        Args:
            job_name: Name of the Jenkins job
            parameters: Optional build parameters

        Returns:
            Queue item ID for tracking the build
        """
        session = await self._get_session()

        # Build the URL
        base_url = self.config.url.rstrip("/")
        if parameters:
            url = f"{base_url}/job/{job_name}/buildWithParameters"
        else:
            url = f"{base_url}/job/{job_name}/build"

        async with session.post(url, data=parameters) as response:
            if response.status not in (200, 201):
                raise Exception(f"Failed to trigger build: {response.status}")

            # Get queue location from header
            queue_url = response.headers.get("Location", "")
            if queue_url:
                # Extract queue ID from URL
                queue_id = int(queue_url.rstrip("/").split("/")[-1])
                return queue_id

            return 0

    async def get_queue_item(self, queue_id: int) -> Optional[int]:
        """
        Get build number from queue item.

        Args:
            queue_id: Queue item ID

        Returns:
            Build number if available, None if still queued
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/queue/item/{queue_id}/api/json"

        async with session.get(url) as response:
            if response.status != 200:
                return None

            data = await response.json()
            executable = data.get("executable")
            if executable:
                return executable.get("number")
            return None

    async def wait_for_build_start(
        self,
        queue_id: int,
        timeout: Optional[int] = None
    ) -> int:
        """
        Wait for a queued build to start.

        Args:
            queue_id: Queue item ID
            timeout: Max wait time in seconds

        Returns:
            Build number once started

        Raises:
            TimeoutError: If build doesn't start within timeout
        """
        timeout = timeout or self.config.timeout_seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            build_number = await self.get_queue_item(queue_id)
            if build_number:
                return build_number

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Build did not start within {timeout} seconds")

            await asyncio.sleep(self.config.poll_interval_seconds)

    async def get_build_info(
        self,
        job_name: str,
        build_number: int
    ) -> JenkinsBuildInfo:
        """
        Get information about a specific build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            JenkinsBuildInfo with build details
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/job/{job_name}/{build_number}/api/json"

        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get build info: {response.status}")

            data = await response.json()

            # Determine status
            if data.get("building"):
                status = BuildStatus.RUNNING
            else:
                result = data.get("result", "PENDING")
                status = BuildStatus(result) if result else BuildStatus.PENDING

            return JenkinsBuildInfo(
                job_name=job_name,
                build_number=build_number,
                status=status,
                result=data.get("result"),
                duration_ms=data.get("duration", 0),
                timestamp=datetime.fromtimestamp(data.get("timestamp", 0) / 1000),
                url=data.get("url", ""),
                artifacts=data.get("artifacts", []),
                console_url=f"{base_url}/job/{job_name}/{build_number}/console"
            )

    async def wait_for_build(
        self,
        job_name: str,
        build_number: int,
        timeout: Optional[int] = None
    ) -> JenkinsBuildInfo:
        """
        Wait for a build to complete.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number
            timeout: Max wait time in seconds

        Returns:
            JenkinsBuildInfo with final build status

        Raises:
            TimeoutError: If build doesn't complete within timeout
        """
        timeout = timeout or self.config.timeout_seconds
        start_time = asyncio.get_event_loop().time()

        while True:
            info = await self.get_build_info(job_name, build_number)

            if info.status not in (BuildStatus.RUNNING, BuildStatus.PENDING):
                return info

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Build did not complete within {timeout} seconds")

            await asyncio.sleep(self.config.poll_interval_seconds)

    async def get_build_artifacts(
        self,
        job_name: str,
        build_number: int
    ) -> list[dict]:
        """
        Get artifacts from a completed build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            List of artifact metadata dicts
        """
        info = await self.get_build_info(job_name, build_number)
        return info.artifacts

    async def get_console_output(
        self,
        job_name: str,
        build_number: int
    ) -> str:
        """
        Get console output from a build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            Console output text
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/job/{job_name}/{build_number}/consoleText"

        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get console output: {response.status}")
            return await response.text()

    async def cancel_build(
        self,
        job_name: str,
        build_number: int
    ) -> bool:
        """
        Cancel a running build.

        Args:
            job_name: Name of the Jenkins job
            build_number: Build number

        Returns:
            True if cancelled successfully
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/job/{job_name}/{build_number}/stop"

        async with session.post(url) as response:
            return response.status in (200, 302)

    async def trigger_and_wait(
        self,
        job_name: str,
        parameters: Optional[dict] = None,
        timeout: Optional[int] = None
    ) -> JenkinsBuildInfo:
        """
        Trigger a build and wait for it to complete.

        Convenience method that combines trigger, wait for start, and wait for completion.

        Args:
            job_name: Name of the Jenkins job
            parameters: Optional build parameters
            timeout: Max wait time in seconds

        Returns:
            JenkinsBuildInfo with final build status
        """
        queue_id = await self.trigger_build(job_name, parameters)
        build_number = await self.wait_for_build_start(queue_id, timeout)
        return await self.wait_for_build(job_name, build_number, timeout)
