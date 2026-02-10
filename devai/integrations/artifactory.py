"""Artifactory API integration for artifact management."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from pathlib import Path


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
        import os
        return cls(
            url=os.getenv("ARTIFACTORY_URL", ""),
            username=os.getenv("ARTIFACTORY_USERNAME", ""),
            api_key=os.getenv("ARTIFACTORY_API_KEY", ""),
            default_repository=os.getenv("ARTIFACTORY_REPOSITORY", "libs-release-local"),
            verify_ssl=os.getenv("ARTIFACTORY_VERIFY_SSL", "true").lower() == "true",
            timeout_seconds=int(os.getenv("ARTIFACTORY_TIMEOUT", "120")),
        )


@dataclass
class ArtifactMetadata:
    """Metadata for an artifact in Artifactory."""
    repository: str
    path: str
    name: str
    version: str
    size_bytes: int = 0
    sha256: str = ""
    md5: str = ""
    created: Optional[datetime] = None
    created_by: str = ""
    download_uri: str = ""
    properties: dict = field(default_factory=dict)


class ArtifactoryClient:
    """
    Async client for Artifactory API operations.

    Provides methods to upload, download, and manage artifacts.
    """

    def __init__(self, config: ArtifactoryConfig):
        self.config = config
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None:
            try:
                import aiohttp
                headers = {
                    "X-JFrog-Art-Api": self.config.api_key,
                }
                connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl)
                self._session = aiohttp.ClientSession(
                    headers=headers,
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                )
            except ImportError:
                raise ImportError("aiohttp is required for Artifactory integration. Install with: pip install aiohttp")
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    @staticmethod
    def compute_checksums(file_path: Path) -> tuple[str, str]:
        """
        Compute SHA-256 and MD5 checksums for a file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (sha256, md5) hex digests
        """
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
                md5.update(chunk)

        return sha256.hexdigest(), md5.hexdigest()

    async def upload_artifact(
        self,
        local_path: Path,
        repository: Optional[str] = None,
        target_path: str = "",
        properties: Optional[dict] = None
    ) -> ArtifactMetadata:
        """
        Upload an artifact to Artifactory.

        Args:
            local_path: Path to the local file
            repository: Repository name (uses default if not specified)
            target_path: Target path in the repository
            properties: Optional properties to set on the artifact

        Returns:
            ArtifactMetadata with upload details including checksums
        """
        session = await self._get_session()
        repository = repository or self.config.default_repository

        # Compute checksums before upload
        sha256, md5 = self.compute_checksums(local_path)

        # Build the URL
        base_url = self.config.url.rstrip("/")
        full_path = f"{target_path}/{local_path.name}" if target_path else local_path.name
        url = f"{base_url}/{repository}/{full_path}"

        # Add checksums and properties to headers
        headers = {
            "X-Checksum-Sha256": sha256,
            "X-Checksum-Md5": md5,
        }

        # Add properties as matrix parameters
        if properties:
            props = ";".join(f"{k}={v}" for k, v in properties.items())
            url = f"{url};{props}"

        # Read and upload file
        with open(local_path, "rb") as f:
            file_data = f.read()

        async with session.put(url, data=file_data, headers=headers) as response:
            if response.status not in (200, 201):
                text = await response.text()
                raise Exception(f"Failed to upload artifact: {response.status} - {text}")

            return ArtifactMetadata(
                repository=repository,
                path=full_path,
                name=local_path.name,
                version=properties.get("version", "") if properties else "",
                size_bytes=len(file_data),
                sha256=sha256,
                md5=md5,
                created=datetime.now(),
                created_by=self.config.username,
                download_uri=url.split(";")[0],  # Remove properties from URL
                properties=properties or {}
            )

    async def download_artifact(
        self,
        repository: str,
        artifact_path: str,
        local_path: Path
    ) -> Path:
        """
        Download an artifact from Artifactory.

        Args:
            repository: Repository name
            artifact_path: Path to the artifact in the repository
            local_path: Local path to save the file

        Returns:
            Path to the downloaded file
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/{repository}/{artifact_path}"

        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download artifact: {response.status}")

            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(local_path, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

        return local_path

    async def get_artifact_info(
        self,
        repository: str,
        artifact_path: str
    ) -> ArtifactMetadata:
        """
        Get metadata about an artifact.

        Args:
            repository: Repository name
            artifact_path: Path to the artifact

        Returns:
            ArtifactMetadata with artifact details
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/api/storage/{repository}/{artifact_path}"

        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get artifact info: {response.status}")

            data = await response.json()

            # Parse created timestamp
            created = None
            if data.get("created"):
                created = datetime.fromisoformat(data["created"].replace("Z", "+00:00"))

            checksums = data.get("checksums", {})

            return ArtifactMetadata(
                repository=repository,
                path=artifact_path,
                name=artifact_path.split("/")[-1],
                version="",  # Would need to parse from path
                size_bytes=int(data.get("size", 0)),
                sha256=checksums.get("sha256", ""),
                md5=checksums.get("md5", ""),
                created=created,
                created_by=data.get("createdBy", ""),
                download_uri=data.get("downloadUri", ""),
                properties={}
            )

    async def set_properties(
        self,
        repository: str,
        artifact_path: str,
        properties: dict
    ) -> bool:
        """
        Set properties on an artifact.

        Args:
            repository: Repository name
            artifact_path: Path to the artifact
            properties: Properties to set

        Returns:
            True if successful
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")

        # Build properties string
        props = ";".join(f"{k}={v}" for k, v in properties.items())
        url = f"{base_url}/api/storage/{repository}/{artifact_path}?properties={props}"

        async with session.put(url) as response:
            return response.status in (200, 204)

    async def get_properties(
        self,
        repository: str,
        artifact_path: str
    ) -> dict:
        """
        Get properties of an artifact.

        Args:
            repository: Repository name
            artifact_path: Path to the artifact

        Returns:
            Dictionary of properties
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/api/storage/{repository}/{artifact_path}?properties"

        async with session.get(url) as response:
            if response.status != 200:
                return {}

            data = await response.json()
            # Artifactory returns properties as {"key": ["value1", "value2"]}
            # Flatten to {"key": "value1"} for single values
            properties = {}
            for key, values in data.get("properties", {}).items():
                properties[key] = values[0] if len(values) == 1 else values
            return properties

    async def search_by_properties(
        self,
        properties: dict,
        repository: Optional[str] = None
    ) -> list[ArtifactMetadata]:
        """
        Search for artifacts by properties.

        Args:
            properties: Properties to search for
            repository: Optional repository to limit search

        Returns:
            List of matching artifact metadata
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")

        # Build AQL query
        props_clauses = [f'"@{k}": "{v}"' for k, v in properties.items()]
        props_query = ", ".join(props_clauses)

        repo_clause = f'"repo": "{repository}",' if repository else ""

        aql = f"""items.find({{
            {repo_clause}
            {props_query}
        }})"""

        url = f"{base_url}/api/search/aql"

        async with session.post(url, data=aql, headers={"Content-Type": "text/plain"}) as response:
            if response.status != 200:
                return []

            data = await response.json()
            results = []

            for item in data.get("results", []):
                results.append(ArtifactMetadata(
                    repository=item.get("repo", ""),
                    path=f"{item.get('path', '')}/{item.get('name', '')}",
                    name=item.get("name", ""),
                    version="",
                    size_bytes=int(item.get("size", 0)),
                    sha256="",
                    md5="",
                    created=None,
                    created_by=item.get("created_by", ""),
                    download_uri="",
                    properties={}
                ))

            return results

    async def get_versions(
        self,
        repository: str,
        artifact_group: str,
        artifact_name: str
    ) -> list[str]:
        """
        Get all versions of an artifact.

        Useful for rollback support.

        Args:
            repository: Repository name
            artifact_group: Group/path prefix (e.g., "com/company/myapp")
            artifact_name: Artifact name

        Returns:
            List of version strings, sorted newest first
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")

        # List folder contents
        url = f"{base_url}/api/storage/{repository}/{artifact_group}/{artifact_name}"

        async with session.get(url) as response:
            if response.status != 200:
                return []

            data = await response.json()
            versions = []

            for child in data.get("children", []):
                if child.get("folder"):
                    # Child folders are versions
                    version = child.get("uri", "").strip("/")
                    if version:
                        versions.append(version)

            # Sort versions (simple string sort - could be improved with semver)
            versions.sort(reverse=True)
            return versions

    async def delete_artifact(
        self,
        repository: str,
        artifact_path: str
    ) -> bool:
        """
        Delete an artifact.

        Requires elevated permissions.

        Args:
            repository: Repository name
            artifact_path: Path to the artifact

        Returns:
            True if deleted successfully
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/{repository}/{artifact_path}"

        async with session.delete(url) as response:
            return response.status in (200, 204)

    async def copy_artifact(
        self,
        source_repo: str,
        source_path: str,
        target_repo: str,
        target_path: str
    ) -> bool:
        """
        Copy an artifact within Artifactory.

        Args:
            source_repo: Source repository
            source_path: Source artifact path
            target_repo: Target repository
            target_path: Target path

        Returns:
            True if copied successfully
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/api/copy/{source_repo}/{source_path}?to=/{target_repo}/{target_path}"

        async with session.post(url) as response:
            return response.status in (200, 201)

    async def move_artifact(
        self,
        source_repo: str,
        source_path: str,
        target_repo: str,
        target_path: str
    ) -> bool:
        """
        Move an artifact within Artifactory.

        Args:
            source_repo: Source repository
            source_path: Source artifact path
            target_repo: Target repository
            target_path: Target path

        Returns:
            True if moved successfully
        """
        session = await self._get_session()
        base_url = self.config.url.rstrip("/")
        url = f"{base_url}/api/move/{source_repo}/{source_path}?to=/{target_repo}/{target_path}"

        async with session.post(url) as response:
            return response.status in (200, 201)
