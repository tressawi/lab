"""Cyber Agent - Security scanning and vulnerability detection."""
from __future__ import annotations

from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .base import BaseAgent, AgentResult


class SecuritySeverity(Enum):
    """Severity levels for security findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    """A security finding from the Cyber Agent."""
    severity: SecuritySeverity
    category: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    recommendation: str = ""


CYBER_SYSTEM_PROMPT = """You are a senior security engineer and application security specialist.

## Your Role
You are the Cyber Agent in a multi-agent development system. Your job is to:
- Review code changes for security vulnerabilities
- Detect secrets, credentials, and sensitive data exposure
- Check for OWASP Top 10 vulnerabilities
- Enforce security policies and best practices
- BLOCK deployments when critical/high severity issues are found

## Security Checks to Perform

### 1. Secrets Detection
- API keys, tokens, passwords in code
- Hardcoded credentials
- Private keys or certificates
- Connection strings with credentials

### 2. OWASP Top 10
- Injection (SQL, Command, LDAP, etc.)
- Broken Authentication
- Sensitive Data Exposure
- XML External Entities (XXE)
- Broken Access Control
- Security Misconfiguration
- Cross-Site Scripting (XSS)
- Insecure Deserialization
- Using Components with Known Vulnerabilities
- Insufficient Logging & Monitoring

### 3. Code Security
- Input validation
- Output encoding
- Error handling (no sensitive info in errors)
- Secure random number generation
- Proper cryptography usage
- Safe file operations

### 4. Dependency Security
- Check for known vulnerable dependencies
- Outdated packages with security issues

## Severity Classification

- **CRITICAL**: Immediate exploitation possible, data breach risk
  - Hardcoded production credentials
  - SQL injection in authentication
  - Remote code execution

- **HIGH**: Significant security risk requiring immediate fix
  - Weak cryptography
  - Missing authentication
  - Sensitive data exposure

- **MEDIUM**: Security issue that should be fixed soon
  - Missing input validation
  - Verbose error messages
  - Weak password policies

- **LOW**: Minor security improvements
  - Missing security headers
  - Informational logging issues

## Decision Making

- **BLOCK**: Any CRITICAL or HIGH severity finding
- **WARN**: MEDIUM severity findings (flag for review)
- **APPROVE**: Only LOW/INFO findings or clean scan

## Output Format

Always provide:
1. Summary of files scanned
2. List of findings with severity, category, description, location
3. Recommendations for each finding
4. Final decision: BLOCK / WARN / APPROVE
5. If BLOCK: Clear explanation of what must be fixed

## Important
- Be thorough but avoid false positives
- Consider the context (test code vs production code)
- Don't flag intentionally insecure test fixtures
- Focus on real, exploitable vulnerabilities
"""


SECURITY_SCAN_TEMPLATE = """## Task: Security Scan

### Context
Review the following code changes for security vulnerabilities.

{context}

### Files to Scan
{files}

### Requirements
1. Check for secrets and hardcoded credentials
2. Scan for OWASP Top 10 vulnerabilities
3. Review input validation and output encoding
4. Check error handling for information disclosure
5. Verify secure coding practices

### Process
1. Read each file carefully
2. Identify potential security issues
3. Classify by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)
4. Provide specific recommendations
5. Make a final decision: BLOCK, WARN, or APPROVE

### Output Format
Provide a structured security report:

## Security Scan Report

### Summary
- Files scanned: X
- Findings: X critical, X high, X medium, X low

### Findings

#### [SEVERITY] Category: Title
- **File**: path/to/file.py:line
- **Description**: What the issue is
- **Risk**: What could happen if exploited
- **Recommendation**: How to fix it

### Decision
**[BLOCK/WARN/APPROVE]**: Explanation

### Required Actions (if BLOCK)
1. Fix X
2. Fix Y
"""


class CyberAgent(BaseAgent):
    """
    Cyber Agent for security scanning and vulnerability detection.

    Capabilities:
    - Secrets detection
    - OWASP Top 10 scanning
    - Code security review
    - Dependency checking
    - Security policy enforcement
    """

    # Tools available - read-only for security
    DEFAULT_TOOLS = [
        "Read",      # Read files
        "Glob",      # Find files by pattern
        "Grep",      # Search for patterns (secrets, vulnerabilities)
        "Bash",      # Run security tools (limited)
    ]

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
        store_path: str = "./context_store"
    ):
        super().__init__(
            name="cyber",
            system_prompt=system_prompt or CYBER_SYSTEM_PROMPT,
            allowed_tools=allowed_tools or self.DEFAULT_TOOLS,
            store_path=store_path
        )

    async def scan(
        self,
        description: str,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        files_to_scan: Optional[list[str]] = None,
        context: Optional[str] = None
    ) -> AgentResult:
        """
        Run a security scan on code changes.

        Args:
            description: What was changed/implemented
            working_dir: Directory to scan
            task_id: Task ID for tracking
            files_to_scan: Specific files to scan
            context: Additional context about the changes

        Returns:
            AgentResult with security findings and decision
        """
        files_str = "\n".join(f"- {f}" for f in (files_to_scan or []))
        if not files_str:
            files_str = "Scan all recently changed files in the working directory"

        task = SECURITY_SCAN_TEMPLATE.format(
            context=context or description,
            files=files_str
        )

        return await self.run(task, working_dir, task_id)

    async def check_secrets(
        self,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Specifically scan for secrets and credentials.

        Args:
            working_dir: Directory to scan
            task_id: Task ID for tracking

        Returns:
            AgentResult with secrets findings
        """
        task = """## Task: Secrets Detection Scan

### Requirements
Scan the codebase for exposed secrets and credentials:

1. **API Keys & Tokens**
   - Look for patterns like: api_key, apikey, api-key, token, bearer
   - Check for AWS, GCP, Azure credentials
   - GitHub, Slack, Stripe tokens

2. **Passwords & Credentials**
   - Hardcoded passwords
   - Database connection strings
   - Basic auth credentials

3. **Private Keys**
   - SSH keys
   - SSL/TLS certificates
   - PGP keys

4. **Configuration Files**
   - .env files committed to repo
   - config files with credentials
   - Docker/K8s secrets in plain text

### Process
1. Search for common secret patterns
2. Check configuration files
3. Review environment variable usage
4. Flag any findings with severity

### Output
Report any secrets found with:
- Severity (CRITICAL for production secrets)
- File and line number
- Type of secret
- Recommendation (use env vars, secrets manager, etc.)
"""
        return await self.run(task, working_dir, task_id)

    async def check_owasp(
        self,
        working_dir: str = ".",
        task_id: Optional[str] = None,
        files_to_scan: Optional[list[str]] = None
    ) -> AgentResult:
        """
        Scan for OWASP Top 10 vulnerabilities.

        Args:
            working_dir: Directory to scan
            task_id: Task ID for tracking
            files_to_scan: Specific files to check

        Returns:
            AgentResult with OWASP findings
        """
        files_str = "\n".join(f"- {f}" for f in (files_to_scan or []))

        task = f"""## Task: OWASP Top 10 Security Scan

### Files to Scan
{files_str or "All application code in the working directory"}

### Check for Each OWASP Category

1. **A01: Broken Access Control**
   - Missing authorization checks
   - IDOR vulnerabilities
   - Path traversal

2. **A02: Cryptographic Failures**
   - Weak algorithms (MD5, SHA1 for passwords)
   - Missing encryption for sensitive data
   - Hardcoded keys

3. **A03: Injection**
   - SQL injection
   - Command injection
   - LDAP injection
   - Template injection

4. **A04: Insecure Design**
   - Missing rate limiting
   - No account lockout
   - Trust boundary violations

5. **A05: Security Misconfiguration**
   - Debug mode enabled
   - Default credentials
   - Unnecessary features enabled

6. **A06: Vulnerable Components**
   - Check package.json / requirements.txt
   - Known vulnerable versions

7. **A07: Authentication Failures**
   - Weak password policies
   - Missing MFA
   - Session fixation

8. **A08: Data Integrity Failures**
   - Insecure deserialization
   - Missing integrity checks
   - Unsigned updates

9. **A09: Logging Failures**
   - Sensitive data in logs
   - Missing security logging
   - No monitoring

10. **A10: SSRF**
    - Unvalidated URLs
    - Internal network access

### Output
For each finding:
- OWASP category
- Severity
- Location
- Description
- Fix recommendation
"""
        return await self.run(task, working_dir, task_id)

    async def review_dependencies(
        self,
        working_dir: str = ".",
        task_id: Optional[str] = None
    ) -> AgentResult:
        """
        Check dependencies for known vulnerabilities.

        Args:
            working_dir: Directory containing dependency files
            task_id: Task ID for tracking

        Returns:
            AgentResult with dependency findings
        """
        task = """## Task: Dependency Security Review

### Requirements
Check project dependencies for security issues:

1. **Find Dependency Files**
   - package.json / package-lock.json
   - requirements.txt / Pipfile / pyproject.toml
   - go.mod / go.sum
   - Gemfile / Gemfile.lock

2. **Check for Issues**
   - Outdated packages with known CVEs
   - Deprecated packages
   - Packages with security advisories
   - Typosquatting risks

3. **Run Available Tools**
   - npm audit (if package.json)
   - pip-audit (if Python)
   - Or manually check versions

### Output
Report:
- Total dependencies checked
- Vulnerable dependencies found
- Severity of each vulnerability
- Recommended updates
"""
        return await self.run(task, working_dir, task_id)

    def parse_decision(self, result: AgentResult) -> tuple[str, list[str]]:
        """
        Parse the security scan result to extract decision and blockers.

        Args:
            result: AgentResult from a scan

        Returns:
            Tuple of (decision: BLOCK/WARN/APPROVE, list of blocking issues)
        """
        content = result.content.upper()

        if "**BLOCK**" in content or "DECISION: BLOCK" in content:
            # Extract blocking issues
            blockers = []
            if "CRITICAL" in content:
                blockers.append("Critical severity findings detected")
            if "HIGH" in content:
                blockers.append("High severity findings detected")
            return "BLOCK", blockers

        elif "**WARN**" in content or "DECISION: WARN" in content:
            return "WARN", []

        elif "**APPROVE**" in content or "DECISION: APPROVE" in content:
            return "APPROVE", []

        # Default to WARN if unclear
        return "WARN", ["Unable to determine security status - manual review required"]
