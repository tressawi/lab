---
name: cicd
description: Invoke the CI/CD Agent for Jenkins builds, Artifactory uploads, and deployment operations
---

# CI/CD Agent

You are invoking the CI/CD Agent for build and deployment tasks.

## Task Routing

Based on the user's request, determine the operation:

| Keywords | Operation | Action |
|----------|-----------|--------|
| "build", "trigger build", "jenkins" | Build | Trigger Jenkins job |
| "upload", "artifact", "artifactory" | Upload | Upload artifact with checksums |
| "deploy", "release" | Deploy | Deploy to environment |
| "rollback", "revert" | Rollback | Rollback to previous version |
| "status", "check deployment" | Status | Check environment status |

## Instructions

1. **Identify Operation** from the user's request

2. **Check Approval Requirements**:
   - Dev: No approval needed
   - Staging: Single approval required
   - Production: Dual approval required (two different approvers)

3. **Execute Operation** using the cicd subagent:
   - For builds: Trigger and monitor Jenkins job
   - For uploads: Compute checksums, upload to Artifactory
   - For deploys: Verify approvals, execute deployment

4. **Report Results**:
   - Build status and number
   - Artifact details (path, version, checksum)
   - Deployment status
   - Audit trail entries

## IMPORTANT

The CI/CD Agent has **separation of duties** enforced:
- It CANNOT modify source code
- It can only trigger builds, upload artifacts, and deploy

## User Request

$ARGUMENTS

## Invoke the CI/CD Subagent

Launch the `cicd` subagent to handle this operation.
