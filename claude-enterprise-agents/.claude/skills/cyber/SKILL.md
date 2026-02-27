---
name: cyber
description: Invoke the Cyber Agent for security scanning, secrets detection, and OWASP vulnerability assessment
---

# Cyber Agent

You are invoking the Cyber Agent for a security task.

## Task Routing

Based on the user's request, determine the scan type:

| Keywords | Scan Type | Action |
|----------|-----------|--------|
| "security scan", "scan for vulnerabilities" | Full Scan | Comprehensive security audit |
| "secrets", "credentials", "api keys" | Secrets | Scan for exposed secrets |
| "owasp", "vulnerabilities" | OWASP | OWASP Top 10 scan |
| "dependencies", "packages", "cve" | Dependencies | Check for vulnerable packages |

## Instructions

1. **Identify Scan Type** from the user's request

2. **Query Standards** before starting:
   - Use the architecture-standards MCP server to get security policies
   - "What are our security requirements?"
   - "What are our data classification policies?"

3. **Execute Scan** using the cyber subagent:
   - Perform thorough security analysis
   - Check all relevant categories
   - Classify findings by severity

4. **Make Decision**:
   - **BLOCK**: Critical or High severity findings
   - **WARN**: Medium severity (flag for review)
   - **APPROVE**: Low/Info only or clean

5. **Report Results**:
   - Files scanned
   - Findings by severity
   - Recommendations
   - Final decision (BLOCK/WARN/APPROVE)

## IMPORTANT

The Cyber Agent has READ-ONLY access. It cannot modify code - only scan and report.

## User Request

$ARGUMENTS

## Invoke the Cyber Subagent

Launch the `cyber` subagent to handle this security scan.
