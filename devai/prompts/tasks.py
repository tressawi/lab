"""Task templates for common development workflows."""

# =============================================================================
# DESIGN TEMPLATE - For design-first workflow
# =============================================================================

DESIGN_TEMPLATE = """## Task: Create Design Document for Approval

### Feature Request
{description}

{library_context}

### Design Requirements
Create a comprehensive design document that must be approved before implementation.

### Design Document Structure

#### 1. Overview
- Brief summary of what will be built
- Business/technical justification

#### 2. Component Library Check
- List which components from the library above will be reused
- Justify any decision to NOT use an available component
- **You MUST use library components when available** - do not reinvent the wheel

#### 3. Technical Approach
- Architecture and design patterns to use
- Data models / schemas (if applicable)
- API endpoints (if applicable)
- Integration points with existing code

#### 4. File Changes
- List of files to be created
- List of files to be modified
- Estimated lines of code

#### 5. Dependencies
- New packages/libraries required (justify each)
- Changes to existing dependencies

#### 6. Security Considerations
- Authentication/authorization impact
- Data validation approach
- Potential security risks and mitigations

#### 7. Testing Strategy
- Unit test coverage plan
- Integration test approach
- Edge cases to cover

#### 8. Risks & Open Questions
- Technical risks identified
- Questions that need clarification before implementation
- Assumptions made

### Output Format
Provide the design document in markdown format. This document will be reviewed
and must be approved before implementation can begin.

**IMPORTANT**: Do NOT write any code. This is a design phase only.
"""

# =============================================================================
# FEATURE TEMPLATE - For implementation (after design approval)
# =============================================================================

FEATURE_TEMPLATE = """## Task: Implement New Feature

### Description
{description}

{library_context}

{design_context}

### Requirements
1. Follow our coding standards (see system prompt)
2. **MUST use components from the library when available** - check the library section above
3. Write clean, maintainable code
4. Add appropriate error handling
5. Update any affected documentation or comments

### Process
1. Review the component library above - use existing components instead of writing new code
2. If an approved design exists, follow it exactly
3. Explore the codebase to understand existing patterns
4. Implement the feature incrementally, reusing library components
5. Run linter and fix any issues if a linter is configured
6. Summarize what you built and any decisions made

### Output
When complete, provide:
- List of files created/modified
- **Components reused from library** (list them)
- Key decisions made and why
- Any deviations from the approved design (with justification)
- Any concerns or follow-up items
- Confidence level in the implementation
"""

BUGFIX_TEMPLATE = """## Task: Fix Bug

### Description
{description}

### Process
1. Understand the expected vs actual behavior
2. Locate the relevant code by exploring the codebase
3. Identify the root cause
4. Implement the fix with minimal changes
5. Verify the fix addresses the issue
6. Check for similar issues elsewhere in the codebase

### Output
When complete, provide:
- Root cause analysis
- The fix implemented
- Files modified
- Any related issues found
- Confidence the bug is fully resolved
"""

REFACTOR_TEMPLATE = """## Task: Refactor Code

### Description
{description}

### Constraints
- Maintain existing behavior (no functional changes)
- Keep backwards compatibility unless explicitly told otherwise
- Improve code quality without over-engineering

### Process
1. Understand the current implementation thoroughly
2. Identify specific improvement opportunities
3. Make incremental changes, verifying behavior after each
4. Ensure no functionality is broken

### Output
When complete, provide:
- What was refactored and why
- Before/after comparison (key changes)
- Any risks or follow-up items
- Confidence that behavior is unchanged
"""

CODE_REVIEW_TEMPLATE = """## Task: Review Code

### Description
{description}

### Review Criteria
1. **Correctness**: Does the code do what it's supposed to?
2. **Security**: Any potential vulnerabilities?
3. **Performance**: Any obvious performance issues?
4. **Maintainability**: Is the code readable and well-structured?
5. **Standards**: Does it follow our coding standards?

### Process
1. Read through the code carefully
2. Identify any issues or concerns
3. Note positive aspects as well
4. Provide actionable feedback

### Output
Provide a structured review with:
- Summary (approve/request changes/needs discussion)
- Issues found (severity: critical/major/minor/nitpick)
- Positive observations
- Suggestions for improvement
"""

EXPLORE_TEMPLATE = """## Task: Explore Codebase

### Description
{description}

### Process
1. Start from entry points (main files, index files)
2. Map out the high-level structure
3. Identify key components and their relationships
4. Note any patterns or conventions used

### Output
Provide:
- High-level architecture overview
- Key files and their purposes
- Patterns and conventions observed
- Any concerns or technical debt noticed
"""

CUSTOM_TEMPLATE = """## Task

{description}

### Process
1. Understand what's being asked
2. Explore relevant parts of the codebase
3. Plan your approach
4. Execute incrementally
5. Verify your work

### Output
Provide:
- Summary of what you did
- Files affected
- Key decisions made
- Any follow-up items
"""


def get_template(task_type: str) -> str:
    """Get the appropriate template for a task type."""
    templates = {
        "feature": FEATURE_TEMPLATE,
        "bugfix": BUGFIX_TEMPLATE,
        "refactor": REFACTOR_TEMPLATE,
        "review": CODE_REVIEW_TEMPLATE,
        "explore": EXPLORE_TEMPLATE,
        "custom": CUSTOM_TEMPLATE,
        "design": DESIGN_TEMPLATE,
    }
    return templates.get(task_type, CUSTOM_TEMPLATE)


def build_design_prompt(description: str, library_context: str = "") -> str:
    """Build a design document prompt."""
    return DESIGN_TEMPLATE.format(
        description=description,
        library_context=library_context or "No matching components found in the library."
    )


def build_task_prompt(
    task_type: str,
    description: str,
    library_context: str = "",
    approved_design: str = None
) -> str:
    """Build a complete task prompt from a template."""
    template = get_template(task_type)

    # Build design context if an approved design exists
    design_context = ""
    if approved_design:
        design_context = f"""### Approved Design (FOLLOW THIS)
The following design has been approved. Implement according to this design:

{approved_design}
"""

    # For feature template, include library and design context
    if task_type == "feature":
        return template.format(
            description=description,
            library_context=library_context or "No matching components found in the library.",
            design_context=design_context
        )

    # For other templates, just use description
    return template.format(description=description)
