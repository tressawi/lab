# CI/CD Agent Technical Design

## Overview

The CI/CD Agent is the 5th agent in the DevAI pipeline, responsible for Jenkins builds, Artifactory artifact management, and deployments.

```
Design → Dev → Test → Cyber → CI/CD
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                 BUILD       ARTIFACT      DEPLOY
                (Jenkins)   (Artifactory)  (env)
```

---

## Separation of Duties

The CI/CD Agent enforces separation through tool restrictions:

```python
class CICDAgent(BaseAgent):
    # Read-only tools - CANNOT modify source code
    DEFAULT_TOOLS = ["Read", "Bash", "Glob", "Grep"]

    # Explicitly EXCLUDED: "Write", "Edit"
```

| Agent | Can Write Code | Can Deploy |
|-------|----------------|------------|
| Dev Agent | Yes | No |
| Test Agent | Tests only | No |
| Cyber Agent | No | No |
| CI/CD Agent | No | Yes |

---

## Agent Methods

| Method | Purpose |
|--------|---------|
| `trigger_build(job_name, parameters)` | Start Jenkins job |
| `upload_artifact(path, repository, version)` | Upload to Artifactory |
| `deploy(environment, artifact_version)` | Deploy to target env |
| `rollback(environment, target_version, reason)` | Revert deployment |

---

## Environment Strategy

| Environment | Auto Deploy | Approval |
|-------------|-------------|----------|
| dev | Yes | None |
| staging | No | Single |
| prod | No | Dual (two different approvers) |

---

## Jenkins Integration

```python
@dataclass
class JenkinsConfig:
    url: str                    # https://jenkins.company.com
    username: str               # Service account
    api_token: str              # From environment variable
    timeout_seconds: int = 600

class JenkinsClient:
    async def trigger_build(self, job_name: str, params: dict) -> int
    async def wait_for_build(self, job_name: str, build_num: int) -> BuildInfo
    async def get_build_artifacts(self, job_name: str, build_num: int) -> list
```

---

## Artifactory Integration

```python
@dataclass
class ArtifactoryConfig:
    url: str                    # https://artifactory.company.com
    username: str               # Service account
    api_key: str                # From environment variable
    default_repository: str     # libs-release-local

class ArtifactoryClient:
    async def upload_artifact(self, local_path, repo, target, props) -> Metadata
    async def download_artifact(self, repo, path, local_path) -> Path
    async def get_versions(self, repo, group, name) -> list[str]
```

---

## Audit Events

```json
{
  "event": "build_trigger",
  "job_name": "my-app-build",
  "build_number": 142,
  "triggered_by": "cicd-agent",
  "pipeline_id": "pipeline-abc123"
}

{
  "event": "artifact_upload",
  "version": "1.0.142",
  "sha256": "abc123...",
  "repository": "libs-release-local"
}

{
  "event": "deployment",
  "environment": "prod",
  "artifact_version": "1.0.142",
  "approved_by": ["alice@company.com", "bob@company.com"]
}
```

---

## Configuration

```bash
# Jenkins
JENKINS_URL=https://jenkins.company.com
JENKINS_USERNAME=devai-service-account
JENKINS_API_TOKEN=<secret>

# Artifactory
ARTIFACTORY_URL=https://artifactory.company.com
ARTIFACTORY_USERNAME=devai-service-account
ARTIFACTORY_API_KEY=<secret>
ARTIFACTORY_REPOSITORY=libs-release-local

# Deployment
DEV_AUTO_DEPLOY=true
STAGING_AUTO_DEPLOY=false
PROD_DUAL_APPROVAL=true
```

---

## CLI Usage

```bash
# Pipeline with staging deployment
devai --pipeline --task "Add feature" --deploy staging

# Production deployment (dual approval)
devai --pipeline --task "Release v1.2" --deploy prod

# Rollback
devai --rollback --deploy prod --artifact-version 1.0.141
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `agents/cicd_agent.py` | Agent implementation |
| `integrations/jenkins.py` | Jenkins API client |
| `integrations/artifactory.py` | Artifactory API client |

## Files to Modify

| File | Changes |
|------|---------|
| `pipeline.py` | Add BUILD, ARTIFACT, DEPLOY stages |
| `approval.py` | Add dual approval for prod |
| `agents/utilities/audit.py` | Add CI/CD audit events |
| `config.py` | Add Jenkins/Artifactory configs |
| `cli.py` | Add --deploy, --rollback flags |
