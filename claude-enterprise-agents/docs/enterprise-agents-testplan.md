# Enterprise Agents Test Plan

## Overview

**Project:** Claude Enterprise Agents
**Version:** 1.0

## Scope

### In Scope

- Agent functionality (dev, test, cyber, cicd)
- MCP server operations (architecture-standards, cicd-integration, approval-gateway)
- Skills routing (/dev, /test, /cyber, /cicd, /pipeline)
- Pipeline orchestration
- Approval workflows
- Installation script

### Out of Scope

- External system availability (Jenkins, Artifactory, Confluence)
- Network connectivity issues
- Claude Code CLI internals

## Test Strategy

### Test Levels

| Level | Description | Tools |
|-------|-------------|-------|
| Unit Tests | Individual MCP server tool functions | Jest/Mocha |
| Integration Tests | Agent-to-MCP server communication | Jest with mocks |
| E2E Tests | Full pipeline execution | Manual + automation |
| Security Tests | Vulnerability and compliance checks | OWASP ZAP, manual review |

### Test Types

- [x] Functional testing
- [x] Integration testing
- [x] Security testing
- [x] Installation testing
- [x] Regression testing

## Test Environment

| Environment | Purpose | Requirements |
|-------------|---------|--------------|
| Local | Development testing | Node.js >= 18, npm |
| CI | Automated testing | GitHub Actions / Jenkins |
| Staging | Pre-production validation | Full external system access |

## Test Cases

### 1. Agent Functionality

#### 1.1 Dev Agent

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| DEV-001 | Create design document | Invoke /dev with feature request | Design document created in docs/ | High |
| DEV-002 | Implement feature | Invoke /dev with approved design | Code changes match design | High |
| DEV-003 | Query architecture standards | /dev queries coding standards | Standards retrieved from MCP | Medium |
| DEV-004 | Request code review approval | /dev requests approval | Approval request created | High |

#### 1.2 Test Agent

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| TEST-001 | Generate unit tests | Invoke /test for new code | Tests created with >80% coverage | High |
| TEST-002 | Run existing tests | Invoke /test to run tests | Test results reported | High |
| TEST-003 | Coverage verification | /test checks coverage | Coverage report generated | Medium |
| TEST-004 | Query testing standards | /test queries standards | Standards retrieved | Medium |

#### 1.3 Cyber Agent

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| CYBER-001 | Vulnerability scan | Invoke /cyber for security scan | Vulnerabilities identified | High |
| CYBER-002 | Secrets detection | /cyber scans for secrets | Hardcoded secrets flagged | High |
| CYBER-003 | OWASP compliance check | /cyber runs OWASP checks | Compliance report generated | High |
| CYBER-004 | Read-only enforcement | /cyber attempts file modification | Modification blocked (no Write tool) | Critical |

#### 1.4 CI/CD Agent

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| CICD-001 | Trigger Jenkins build | Invoke /cicd to build | Build triggered and monitored | High |
| CICD-002 | Upload artifact | /cicd uploads to Artifactory | Artifact uploaded with checksums | High |
| CICD-003 | Deploy to dev | /cicd deploys to dev | Auto-deploy succeeds | High |
| CICD-004 | Deploy to staging | /cicd deploys to staging | Single approval required | High |
| CICD-005 | Deploy to production | /cicd deploys to prod | Dual approval required | Critical |
| CICD-006 | Read-only enforcement | /cicd attempts file modification | Modification blocked | Critical |

### 2. MCP Server Operations

#### 2.1 architecture-standards

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| ARCH-001 | Get architecture patterns | Call get_architecture_patterns | Patterns returned | High |
| ARCH-002 | Get security standards | Call get_security_standards | Standards returned | High |
| ARCH-003 | Search standards | Call search_standards with query | Search results returned | Medium |
| ARCH-004 | Cache behavior | Call same endpoint twice | Second call uses cache | Low |
| ARCH-005 | Missing credentials | Start without env vars | Graceful error message | Medium |

#### 2.2 cicd-integration

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| CI-001 | Trigger build | Call trigger_jenkins_build | Build queued and ID returned | High |
| CI-002 | Get build status | Call get_build_status | Status returned (SUCCESS/FAILURE/BUILDING) | High |
| CI-003 | Upload artifact | Call upload_artifact | Artifact uploaded with SHA-256/MD5 | High |
| CI-004 | Get artifact info | Call get_artifact_info | Metadata returned | Medium |
| CI-005 | Checksum verification | Upload with wrong checksum | Upload rejected | High |

#### 2.3 approval-gateway

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| APPR-001 | Request single approval | Call request_approval | Request created with pending status | High |
| APPR-002 | Request dual approval | Call request_dual_approval | Request requires 2 approvers | High |
| APPR-003 | Approve request | Call approve_request | Status changed to approved | High |
| APPR-004 | Reject request | Call reject_request | Status changed to rejected | High |
| APPR-005 | Dual approval same user | Same user approves twice | Second approval rejected | Critical |
| APPR-006 | Audit logging | Complete approval flow | All actions logged | High |
| APPR-007 | List pending approvals | Call list_pending_approvals | Pending requests listed | Medium |

### 3. Pipeline Orchestration

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| PIPE-001 | Full pipeline execution | Invoke /pipeline with feature | All stages complete in order | High |
| PIPE-002 | Pipeline with approval gates | Run pipeline | Pauses at each approval gate | High |
| PIPE-003 | Pipeline security block | Security finds critical issue | Pipeline blocked at security gate | Critical |
| PIPE-004 | Pipeline rollback | Invoke rollback | Previous version deployed | High |

### 4. Installation

| ID | Description | Steps | Expected Result | Priority |
|----|-------------|-------|-----------------|----------|
| INST-001 | Fresh installation | Run npm run install-agents | Agents/skills/MCP configured | High |
| INST-002 | Reinstallation | Run install twice | No errors, files updated | Medium |
| INST-003 | Verify agent locations | Check ~/.claude/agents/ | All 4 agents present | High |
| INST-004 | Verify skill locations | Check ~/.claude/skills/ | All 5 skills present | High |
| INST-005 | Verify MCP config | Check ~/.claude/settings.json | 3 MCP servers configured | High |

## Entry Criteria

- [x] Code complete and merged
- [x] Design document approved
- [x] Test environment configured
- [x] Dependencies installed (Node.js >= 18)

## Exit Criteria

- [ ] All critical test cases passed
- [ ] All high priority test cases passed
- [ ] No critical or high severity bugs open
- [ ] Security scan passed (no critical/high vulnerabilities)
- [ ] Installation verified on clean environment

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| External system unavailable | High | Medium | Mock external APIs for testing |
| Approval workflow deadlock | Medium | Low | Implement timeout handling |
| MCP server crash | High | Low | Error handling and recovery |
| Credentials exposure | Critical | Low | Environment variable validation |

## Defect Management

- **Tracking:** GitHub Issues
- **Severity Levels:** Critical, High, Medium, Low
- **SLA:** Critical - 24h, High - 72h, Medium - 1 week, Low - 2 weeks
