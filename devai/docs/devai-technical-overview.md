# DevAI: Technical Overview for Executive Leadership

## What We Built

DevAI is a **multi-agent AI development system** that automates software development workflows while maintaining human oversight and control. It orchestrates specialized AI agents through a governed pipeline, ensuring quality, security, and compliance at every step.

---

## The Core Innovation: Claude Code SDK

At the heart of DevAI is Anthropic's **Claude Code SDK**—a programmatic interface that gives us direct access to Claude's coding capabilities. This is the same AI engine that powers Claude Code (Anthropic's developer tool), now available as a building block for custom systems.

### How It Works

```
Your Application
      │
      ▼
┌─────────────────────────────────────────┐
│         Claude Code SDK                  │
│                                          │
│  query(prompt, options)                  │
│      │                                   │
│      ▼                                   │
│  Returns stream of AI responses:         │
│  • Text content (explanations, code)     │
│  • Tool executions (read/write files)    │
│  • Session IDs (for conversation memory) │
│                                          │
└─────────────────────────────────────────┘
      │
      ▼
  AI performs tasks in your codebase
```

### The `query()` Function: Our Control Point

The SDK's `query()` function is the single entry point we use to interact with Claude:

| What We Send | What We Get Back |
|--------------|------------------|
| **Prompt**: The task to perform | **Content**: Claude's response and reasoning |
| **System prompt**: Our policies and standards | **Tool results**: Files read, code written, commands run |
| **Allowed tools**: What actions Claude can take | **Session ID**: Memory of the conversation |
| **Working directory**: Where to operate | **Streaming**: Real-time progress updates |

**Key insight**: We control *what* the AI can do by restricting its tools. A security-scanning agent literally cannot modify code—it lacks the tools to do so.

---

## Why This Matters for the Business

### Before: Fragmented AI Tools

```
Developer uses Copilot → Manual code review → Separate security scan → Manual deployment
         ↓                      ↓                      ↓                    ↓
    No governance         Inconsistent           Delayed feedback      Human bottleneck
```

### After: Orchestrated AI Pipeline

```
DevAI Pipeline (Automated, Governed, Auditable)

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  DESIGN  │───►│   DEV    │───►│   TEST   │───►│  CYBER   │
  │  Agent   │    │  Agent   │    │  Agent   │    │  Agent   │
  └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
    Human           Human           Human          Security
   Approval        Approval        Approval         Gate
                                                (BLOCK/WARN/APPROVE)
```

---

## The Four Agents

| Agent | Purpose | What It Can Do | What It Cannot Do |
|-------|---------|----------------|-------------------|
| **Design Agent** | Creates implementation plans | Read code, search patterns, write design docs | Write application code |
| **Dev Agent** | Writes and modifies code | Read, write, edit files; run linters | Deploy to production |
| **Test Agent** | Generates and runs tests | Read code, write test files, run tests | Modify application code |
| **Cyber Agent** | Security scanning | Read all files, run security tools | Modify any files |

**Separation of duties is enforced by tool permissions, not just instructions.**

---

## Design-First Workflow

A key innovation: every feature starts with a **design document** that must be approved before coding begins.

### Why This Matters

1. **Reuse over reinvention**: The design phase checks our component library first
2. **Alignment before effort**: Catch misunderstandings before code is written
3. **Audit trail**: Documented rationale for every implementation decision
4. **Quality gate**: Architectural review happens automatically

### Component Library Integration

We maintain a library of pre-approved, reusable components:

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPONENT LIBRARY                         │
├─────────────────────────────────────────────────────────────┤
│  • Password hashing (bcrypt)     • JWT authentication       │
│  • Email validation              • Rate limiting            │
│  • Input sanitization            • Structured logging       │
│  • HTTP retry client             • Error handling patterns  │
│  • Pydantic models               • Configuration management │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
         Design Agent checks library BEFORE proposing new code
                              │
                              ▼
              "Use existing component" or "Justify new code"
```

**Result**: Consistent patterns, reduced security risk, faster development.

---

## Human-in-the-Loop: Where Humans Stay in Control

| Decision Type | Who Decides | Cannot Be Bypassed |
|---------------|-------------|-------------------|
| Design approval | Technical lead | ✓ |
| Code changes | Developer/reviewer | ✓ |
| Test coverage | QA lead | ✓ |
| Security exceptions | Security team | ✓ |
| Production deployment | Change advisory board | ✓ |

**The AI proposes. Humans approve.**

---

## Security Architecture

### The Cyber Agent: Automated Security Gate

Every change passes through security scanning before completion:

```
Code Changes
     │
     ▼
┌─────────────────────────────────────────┐
│            CYBER AGENT SCAN              │
│                                          │
│  ✓ Secrets detection (API keys, creds)  │
│  ✓ OWASP Top 10 vulnerabilities         │
│  ✓ Input validation checks              │
│  ✓ Dependency vulnerabilities           │
│  ✓ Security best practices              │
│                                          │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│           SECURITY DECISION              │
│                                          │
│  APPROVE → Pipeline continues            │
│  WARN    → Human review required         │
│  BLOCK   → Pipeline stops, must fix      │
│                                          │
└─────────────────────────────────────────┘
```

**Critical/High severity findings automatically BLOCK the pipeline.**

---

## Audit Trail: Complete Visibility

Every action is logged:

| Logged Data | Purpose |
|-------------|---------|
| Timestamp | When it happened |
| Agent ID | Which AI agent acted |
| Action | What was done |
| Input/Output | Full context |
| Decision | Pass/fail/escalate |
| Human approver | Who signed off |
| Correlation ID | Links related actions |

**Retention**: 7 years (configurable)
**Format**: Immutable, append-only, cryptographically signed

---

## Technical Foundation: Two SDK Options

DevAI is built on a provider-agnostic architecture. Today, two production-grade SDKs exist for building agentic coding systems:

| SDK | Status | Provider |
|-----|--------|----------|
| **Claude Code SDK** | GA (Production) | Anthropic |
| **GitHub Copilot SDK** | Technical Preview | GitHub/Microsoft |

---

## Option 1: Claude Code SDK

The Claude Code SDK provides programmatic access to Claude's coding capabilities:

| Capability | Business Value |
|------------|----------------|
| **Programmatic access** | Build custom workflows, not just chat |
| **Tool control** | Enforce what AI can/cannot do |
| **Session memory** | AI remembers context across interactions |
| **Streaming responses** | Real-time visibility into AI work |
| **Permission modes** | Fine-grained security control |

### SDK Integration Point

```python
from claude_code_sdk import query, ClaudeCodeOptions

# Configure what the agent can do
options = ClaudeCodeOptions(
    system_prompt="You are a senior developer following our standards...",
    allowed_tools=["Read", "Write", "Edit", "Bash"],  # Controlled permissions
    cwd="/path/to/project",
    permission_mode="bypassPermissions",  # Or require human approval
)

# Run the agent - async iterator pattern
async for message in query(prompt="Implement user authentication", options=options):
    # Stream of AI responses: content, tool uses, session state
    process(message)
```

**One function. Full control. Complete audit trail.**

---

## Option 2: GitHub Copilot SDK

The Copilot SDK (Technical Preview, January 2025) offers a critical differentiator: **Bring Your Own Key (BYOK)**.

### Why BYOK Matters

```
┌─────────────────────────────────────────────────────────────┐
│              COPILOT SDK: MODEL FLEXIBILITY                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Your Application                                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            GitHub Copilot SDK                        │    │
│  │                                                      │    │
│  │  provider: "openai"     → Use OpenAI GPT-4          │    │
│  │  provider: "azure"      → Use Azure OpenAI          │    │
│  │  provider: "ollama"     → Use local models (FREE)   │    │
│  │  provider: "anthropic"  → Use Claude                │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Copilot SDK Integration Point

```python
from copilot import CopilotClient

client = CopilotClient()
await client.start()

# Create session with YOUR choice of model provider
session = await client.create_session({
    "model": "gpt-4",
    "provider": {
        "type": "azure",  # Or "openai", "ollama" for local
        "base_url": "https://your-azure-resource.openai.azure.com",
    }
})

# Event callback pattern
def on_event(event):
    if event.type.value == "assistant.message":
        print(event.data.content)

session.on(on_event)
await session.send({"prompt": "Implement user authentication"})
```

### Key Differences

| Consideration | Claude Code SDK | Copilot SDK |
|---------------|-----------------|-------------|
| **Model Provider** | Anthropic only | Any (OpenAI, Azure, Ollama, etc.) |
| **Cost** | Anthropic API pricing | Your choice (Ollama = free) |
| **Data Residency** | Anthropic cloud | Your infrastructure possible |
| **Offline/Air-gapped** | No | Yes (with Ollama) |
| **Coding Performance** | Best-in-class | Varies by model |
| **Production Status** | GA | Technical Preview |

---

## Choosing the Right SDK

| Use Case | Recommended SDK |
|----------|-----------------|
| Best coding performance today | Claude Code SDK |
| Cost-sensitive / high volume | Copilot SDK + Ollama |
| Data privacy / air-gapped | Copilot SDK + local models |
| Azure compliance requirements | Copilot SDK + Azure OpenAI |
| Enterprise with strict data residency | Copilot SDK + your infrastructure |

### Our Architecture: Provider-Agnostic

```
┌─────────────────────────────────────────────────────────────┐
│                    DevAI Orchestration                       │
│                                                              │
│  • Design-first workflow                                     │
│  • Component library                                         │
│  • Human approval gates                                      │
│  • Audit trail                                               │
│  • Security scanning                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Backend Abstraction   │
              └────────────────────────┘
                    │           │
          ┌─────────┘           └─────────┐
          ▼                               ▼
   ┌─────────────┐                 ┌─────────────┐
   │ Claude Code │                 │   Copilot   │
   │     SDK     │                 │     SDK     │
   └─────────────┘                 └─────────────┘
          │                               │
          ▼                               ▼
      Anthropic                    Any Provider
       Claude                   (Azure, Ollama, etc.)
```

**The value is in the orchestration layer, not the model.** We can swap backends without changing workflows, approvals, or audit trails.

---

## Summary: What DevAI Delivers

| Capability | How |
|------------|-----|
| **Governed AI** | Tool permissions + human approval gates |
| **Design-first** | Mandatory design review before coding |
| **Reuse enforcement** | Component library integration |
| **Security by default** | Cyber Agent with BLOCK capability |
| **Full auditability** | Every action logged and traceable |
| **Extensible** | Built on Claude Code SDK, supports multiple providers |

---

## Key Takeaway

DevAI is not "AI writing code unsupervised." It's a **governed pipeline** where:

- AI agents handle routine work with superhuman speed
- Humans retain control over all significant decisions
- Security is enforced automatically, not hoped for
- Every action is auditable for compliance

**The Claude Code SDK gives us the building blocks. DevAI adds the governance.**

---

*Document Version: 1.0*
*Last Updated: January 2026*
