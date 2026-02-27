# Enterprise Development Standards

This file contains enterprise-wide development standards that apply to all projects.

## Agent Usage

Use the following slash commands to invoke specialized agents:

- `/dev` - Development tasks (features, bugfixes, refactoring)
- `/test` - Test generation and execution
- `/cyber` - Security scanning and vulnerability assessment
- `/cicd` - Build, deploy, and release operations
- `/pipeline` - Full SDLC pipeline (dev → test → cyber → cicd)

## Design-First Workflow

All feature development MUST follow the design-first approach:
1. Create a design document before writing code
2. Get design approval from appropriate stakeholders
3. Implement following the approved design
4. Do not deviate from approved design without re-approval

## Code Standards

### Before Writing Code
- Query standards using the MCP server: "What are our standards for [topic]?"
- Check for existing reusable components
- Follow approved architecture patterns

### Security Requirements
- No secrets in code (use environment variables or secret management)
- All inputs must be validated
- Follow OWASP Top 10 guidelines
- All dependencies must be scanned for CVEs

### Approval Requirements
- Dev environment: Auto-deploy allowed
- Staging: Single approval required
- Production: Dual approval required (two different approvers)

## Git Commits

- Do not add "Co-Authored-By: Claude" or similar attribution to commit messages
- Do not attribute commits to Claude or any AI assistant

## MCP Servers

This project includes three MCP servers:

1. **architecture-standards** - Retrieves architecture, security, and coding standards from Confluence/SharePoint
2. **cicd-integration** - Jenkins and Artifactory integration for builds and artifacts
3. **approval-gateway** - Human-in-the-loop approval workflow
