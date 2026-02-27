---
name: pipeline
description: Run the full SDLC pipeline - Dev, Test, Cyber, and CI/CD stages with approval gates
---

# Full SDLC Pipeline

You are invoking the full development pipeline that orchestrates all agents.

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Design        → Create design document                │
│      ↓                                                          │
│  [APPROVAL GATE]        → Human approves design                 │
│      ↓                                                          │
│  Stage 2: Development   → Dev Agent implements                  │
│      ↓                                                          │
│  [APPROVAL GATE]        → Human reviews code                    │
│      ↓                                                          │
│  Stage 3: Testing       → Test Agent generates & runs tests     │
│      ↓                                                          │
│  [APPROVAL GATE]        → Human reviews tests                   │
│      ↓                                                          │
│  Stage 4: Security      → Cyber Agent scans for vulnerabilities │
│      ↓                                                          │
│  [SECURITY GATE]        → BLOCK/WARN/APPROVE decision           │
│      ↓                                                          │
│  Stage 5: Build         → CI/CD triggers Jenkins build          │
│      ↓                                                          │
│  Stage 6: Artifact      → Upload to Artifactory                 │
│      ↓                                                          │
│  Stage 7: Deploy Dev    → Auto-deploy to dev                    │
│      ↓                                                          │
│  [APPROVAL GATE]        → Single approval for staging           │
│      ↓                                                          │
│  Stage 8: Deploy Staging                                        │
│      ↓                                                          │
│  [DUAL APPROVAL GATE]   → Two approvers for production          │
│      ↓                                                          │
│  Stage 9: Deploy Prod   → Production deployment                 │
└─────────────────────────────────────────────────────────────────┘
```

## Instructions

1. **Parse Request**: Understand what feature/change is being requested

2. **Stage 1 - Design**:
   - Use the `/dev` skill to create a design document
   - Do NOT proceed to implementation until design is approved
   - Use approval-gateway MCP to request design approval

3. **Stage 2 - Development**:
   - After design approval, use `/dev` skill to implement
   - Follow the approved design exactly
   - Request code review approval

4. **Stage 3 - Testing**:
   - Use `/test` skill to generate tests for the changes
   - Verify coverage meets requirements
   - Request test review approval

5. **Stage 4 - Security**:
   - Use `/cyber` skill to scan all changes
   - If BLOCK: Stop pipeline, report required fixes
   - If WARN: Request human review before proceeding
   - If APPROVE: Continue to build

6. **Stage 5-6 - Build & Artifact**:
   - Use `/cicd` skill to trigger build
   - Upload artifact to Artifactory

7. **Stage 7-9 - Deployments**:
   - Dev: Auto-deploy
   - Staging: Request single approval, then deploy
   - Production: Request dual approval, then deploy

## Approval Gates

Use the approval-gateway MCP server to:
- Request approvals at each gate
- Block until approval is received
- Log all approvals for audit trail

## User Request

$ARGUMENTS

## Execute Pipeline

Orchestrate the full pipeline, invoking each agent in sequence with appropriate approval gates.
