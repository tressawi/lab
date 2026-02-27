# Enterprise Agents Design Document

## Overview

**Project:** Claude Enterprise Agents
**Version:** 1.0
**Status:** Approved

An enterprise SDLC automation platform that provides specialized AI agents for software development lifecycle management with built-in approval gates, security scanning, and CI/CD integration.

## Problem Statement

Enterprise software development faces several challenges:
- Manual handoffs between development, testing, security, and operations teams
- Inconsistent adherence to coding and security standards
- Lack of audit trails for compliance requirements
- Complex approval workflows for production deployments
- Difficulty enforcing separation of duties

## Goals

- Automate software development workflows through specialized AI agents
- Enforce design-first development with mandatory approval gates
- Ensure code quality through automated testing (>80% coverage)
- Maintain security compliance with OWASP scanning and secrets detection
- Implement separation of duties (security agents read-only, CI/CD cannot modify code)
- Provide audit trails for regulatory compliance
- Integrate with enterprise systems (Confluence, SharePoint, Jenkins, Artifactory)

## Non-Goals

- Replacing human decision-making for critical deployments
- Autonomous production deployments without approval
- Modifying security scanning results

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                             │
├─────────────────────────────────────────────────────────────────┤
│  Skills Layer                                                    │
│  /dev    /test    /cyber    /cicd    /pipeline                  │
├─────────────────────────────────────────────────────────────────┤
│  Agents Layer                                                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │   Dev   │  │  Test   │  │  Cyber  │  │  CI/CD  │            │
│  │  Agent  │  │  Agent  │  │  Agent  │  │  Agent  │            │
│  │ (R/W)   │  │ (R/W)   │  │ (R/O)   │  │ (R/O)   │            │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
├───────┴───────────┴───────────┴───────────┴─────────────────────┤
│  MCP Servers                                                     │
│  ┌──────────────────┐ ┌───────────────┐ ┌──────────────────┐    │
│  │  architecture-   │ │    cicd-      │ │    approval-     │    │
│  │    standards     │ │  integration  │ │     gateway      │    │
│  └────────┬─────────┘ └───────┬───────┘ └────────┬─────────┘    │
├───────────┴───────────────────┴──────────────────┴──────────────┤
│  External Systems                                                │
│  Confluence    SharePoint    Jenkins    Artifactory    Jira     │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Agents

| Agent | Role | Tools | Responsibility |
|-------|------|-------|----------------|
| Dev | Senior Software Engineer | Read, Write, Edit, Bash, Glob, Grep | Code development, features, bugfixes, refactoring |
| Test | Senior QA Engineer | Read, Write, Edit, Bash, Glob, Grep | Test generation, execution, coverage verification |
| Cyber | Senior Security Engineer | Read, Bash, Glob, Grep (READ-ONLY) | Vulnerability scanning, secrets detection, OWASP compliance |
| CI/CD | DevOps Engineer | Read, Bash, Glob, Grep (READ-ONLY) | Jenkins builds, Artifactory artifacts, deployments |

### MCP Servers

| Server | Purpose | Tools |
|--------|---------|-------|
| architecture-standards | Retrieve enterprise standards from Confluence/SharePoint | get_architecture_patterns, get_security_standards, get_coding_standards, get_testing_standards, get_component_library, search_standards |
| cicd-integration | Jenkins and Artifactory integration | trigger_jenkins_build, get_build_status, upload_artifact, get_artifact_info, deploy_to_environment, rollback_deployment |
| approval-gateway | Human-in-the-loop approval workflow | request_approval, request_dual_approval, check_approval_status, approve_request, reject_request, get_approval_history, list_pending_approvals |

### Skills

| Skill | Command | Purpose |
|-------|---------|---------|
| dev | `/dev` | Route development tasks to Dev Agent |
| test | `/test` | Route testing tasks to Test Agent |
| cyber | `/cyber` | Route security tasks to Cyber Agent |
| cicd | `/cicd` | Route CI/CD tasks to CI/CD Agent |
| pipeline | `/pipeline` | Orchestrate full SDLC pipeline |

## Data Flow

### Pipeline Execution Flow

```
1. Design Phase
   └── /dev creates design document
   └── [APPROVAL GATE: design_review]

2. Development Phase
   └── /dev implements per approved design
   └── [APPROVAL GATE: code_review]

3. Testing Phase
   └── /test generates and runs tests
   └── [APPROVAL GATE: test_review]

4. Security Phase
   └── /cyber scans for vulnerabilities
   └── [SECURITY GATE: BLOCK/WARN/APPROVE]

5. Build Phase
   └── /cicd triggers Jenkins build
   └── Upload artifact to Artifactory (SHA-256 checksum)

6. Deployment Phase
   └── Dev: Auto-deploy (no approval)
   └── Staging: [SINGLE APPROVAL]
   └── Production: [DUAL APPROVAL - two different approvers]
```

## Security Considerations

- [x] **Separation of Duties**: Cyber and CI/CD agents are read-only (cannot modify source code)
- [x] **Dual Approval**: Production deployments require approval from two different approvers
- [x] **Audit Logging**: All approvals logged with timestamps for compliance
- [x] **Secrets Management**: All credentials via environment variables (never in code)
- [x] **Artifact Integrity**: SHA-256 and MD5 checksums for all artifacts
- [x] **OWASP Compliance**: Security scanning against OWASP Top 10

## Dependencies

| System | Purpose | Configuration |
|--------|---------|---------------|
| Confluence | Architecture standards documentation | CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN |
| SharePoint | Enterprise documentation | SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET |
| Jenkins | Build automation | JENKINS_URL, JENKINS_USERNAME, JENKINS_API_TOKEN |
| Artifactory | Artifact repository | ARTIFACTORY_URL, ARTIFACTORY_USERNAME, ARTIFACTORY_API_KEY |
| ServiceNow | Approval integration (optional) | SERVICENOW_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD |
| Jira | Issue tracking (optional) | JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN |

## Installation

```bash
npm run install-agents
```

This copies agents to `~/.claude/agents/`, skills to `~/.claude/skills/`, and configures MCP servers in `~/.claude/settings.json`.

## Directory Structure

```
claude-enterprise-agents/
├── .claude/
│   ├── agents/
│   │   ├── dev.md
│   │   ├── test.md
│   │   ├── cyber.md
│   │   └── cicd.md
│   └── skills/
│       ├── dev/SKILL.md
│       ├── test/SKILL.md
│       ├── cyber/SKILL.md
│       ├── cicd/SKILL.md
│       └── pipeline/SKILL.md
├── mcp-servers/
│   ├── architecture-standards/
│   ├── cicd-integration/
│   └── approval-gateway/
├── scripts/
│   └── install.js
├── docs/
├── CLAUDE.md
└── package.json
```
