"""Mock reusable component library.

This module provides a searchable library of pre-approved, reusable
components that agents should check before writing new code.

In production, this would connect to:
- Internal package registry
- Approved library catalog
- Enterprise component library
- Design system components
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json


@dataclass
class Component:
    """A reusable component in the library."""
    id: str
    name: str
    category: str
    description: str
    language: str
    usage_example: str
    package: Optional[str] = None  # pip/npm package name
    import_path: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    approved: bool = True
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "language": self.language,
            "usage_example": self.usage_example,
            "package": self.package,
            "import_path": self.import_path,
            "tags": self.tags,
            "approved": self.approved,
            "version": self.version,
        }


# Mock component library - in production, this would be loaded from a database/API
MOCK_COMPONENTS = [
    # Authentication & Security
    Component(
        id="auth-password-hash",
        name="Password Hashing Utility",
        category="security",
        description="Secure password hashing using bcrypt with configurable rounds. Use this for all password storage - never implement custom hashing.",
        language="python",
        package="bcrypt",
        import_path="bcrypt",
        usage_example='''import bcrypt

def hash_password(password: str) -> bytes:
    """Hash a password securely."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def verify_password(password: str, hashed: bytes) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed)''',
        tags=["password", "hash", "security", "bcrypt", "authentication"],
    ),
    Component(
        id="auth-jwt-token",
        name="JWT Token Handler",
        category="security",
        description="JWT token generation and validation. Use for API authentication tokens.",
        language="python",
        package="pyjwt",
        import_path="jwt",
        usage_example='''import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"  # Load from environment

def create_token(user_id: str, expires_hours: int = 24) -> str:
    """Create a JWT token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])''',
        tags=["jwt", "token", "authentication", "api", "security"],
    ),
    Component(
        id="auth-rate-limiter",
        name="Rate Limiter",
        category="security",
        description="Rate limiting decorator for API endpoints. Prevents brute force attacks.",
        language="python",
        package="ratelimit",
        import_path="ratelimit",
        usage_example='''from ratelimit import limits, sleep_and_retry

# 5 calls per minute
@sleep_and_retry
@limits(calls=5, period=60)
def api_endpoint():
    """Rate-limited API endpoint."""
    pass

# Or use with Flask/FastAPI middleware for more control''',
        tags=["rate-limit", "security", "api", "throttle", "brute-force"],
    ),

    # Validation
    Component(
        id="validation-email",
        name="Email Validator",
        category="validation",
        description="RFC-compliant email validation. Use for all email input validation.",
        language="python",
        package="email-validator",
        import_path="email_validator",
        usage_example='''from email_validator import validate_email, EmailNotValidError

def is_valid_email(email: str) -> bool:
    """Validate an email address."""
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

def normalize_email(email: str) -> str:
    """Validate and normalize an email address."""
    result = validate_email(email, check_deliverability=False)
    return result.normalized''',
        tags=["email", "validation", "input", "sanitization"],
    ),
    Component(
        id="validation-input-sanitizer",
        name="Input Sanitizer",
        category="validation",
        description="HTML/XSS sanitization for user input. Use for any user-provided text that will be rendered.",
        language="python",
        package="bleach",
        import_path="bleach",
        usage_example='''import bleach

def sanitize_html(text: str) -> str:
    """Sanitize HTML, allowing only safe tags."""
    allowed_tags = ["b", "i", "u", "em", "strong", "a", "p", "br"]
    allowed_attrs = {"a": ["href", "title"]}
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs)

def strip_all_html(text: str) -> str:
    """Remove all HTML tags."""
    return bleach.clean(text, tags=[], strip=True)''',
        tags=["sanitize", "xss", "html", "security", "input"],
    ),

    # Data & Models
    Component(
        id="data-pydantic-model",
        name="Pydantic Base Model",
        category="data",
        description="Base model pattern using Pydantic for data validation. Use for all API request/response models.",
        language="python",
        package="pydantic",
        import_path="pydantic",
        usage_example='''from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """User creation request model."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: Optional[str] = Field(None, max_length=100)

    @validator("email")
    def email_must_be_valid(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

class UserResponse(BaseModel):
    """User response model (no password)."""
    id: str
    email: str
    name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True  # For ORM compatibility''',
        tags=["pydantic", "model", "validation", "api", "schema"],
    ),

    # Logging & Monitoring
    Component(
        id="logging-structured",
        name="Structured Logger",
        category="observability",
        description="Structured JSON logging for production. Use instead of print statements.",
        language="python",
        package="structlog",
        import_path="structlog",
        usage_example='''import structlog

# Configure once at app startup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# Usage
log = structlog.get_logger()
log.info("user_login", user_id="123", ip_address="192.168.1.1")
log.error("payment_failed", order_id="456", reason="insufficient_funds")''',
        tags=["logging", "structured", "json", "observability", "monitoring"],
    ),

    # HTTP & API
    Component(
        id="http-retry-client",
        name="HTTP Client with Retry",
        category="http",
        description="HTTP client with automatic retry, backoff, and timeout handling.",
        language="python",
        package="httpx",
        import_path="httpx",
        usage_example='''import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_with_retry(url: str) -> dict:
    """Fetch URL with automatic retry on failure."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Synchronous version
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_sync(url: str) -> dict:
    """Synchronous fetch with retry."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()''',
        tags=["http", "api", "retry", "client", "async"],
    ),

    # Testing
    Component(
        id="test-fixtures",
        name="Pytest Fixtures Pattern",
        category="testing",
        description="Standard pytest fixture patterns for database, API, and mock setup.",
        language="python",
        package="pytest",
        import_path="pytest",
        usage_example='''import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = Mock()
    db.query.return_value = []
    yield db
    db.close()

@pytest.fixture
def api_client():
    """Test API client."""
    from myapp import create_app
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client

@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "name": "Test User",
    }''',
        tags=["pytest", "testing", "fixtures", "mock", "unit-test"],
    ),

    # Error Handling
    Component(
        id="error-custom-exceptions",
        name="Custom Exception Hierarchy",
        category="errors",
        description="Standard pattern for custom application exceptions.",
        language="python",
        package=None,
        import_path=None,
        usage_example='''class AppError(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field

class NotFoundError(AppError):
    """Raised when a resource is not found."""
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} not found: {id}", code="NOT_FOUND")
        self.resource = resource
        self.id = id

class AuthenticationError(AppError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTH_ERROR")''',
        tags=["exceptions", "errors", "handling", "patterns"],
    ),

    # Configuration
    Component(
        id="config-settings",
        name="Settings with Pydantic",
        category="configuration",
        description="Type-safe configuration management using pydantic-settings.",
        language="python",
        package="pydantic-settings",
        import_path="pydantic_settings",
        usage_example='''from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # API
    api_key: str = Field(..., env="API_KEY")
    debug: bool = Field(False, env="DEBUG")

    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage
settings = Settings()
print(settings.database_url)''',
        tags=["config", "settings", "environment", "pydantic"],
    ),
]


class ComponentLibrary:
    """
    Searchable library of reusable components.

    Agents should check this library before implementing new functionality
    to promote code reuse and consistency.
    """

    def __init__(self, components: list[Component] = None):
        self.components = components or MOCK_COMPONENTS
        self._index = self._build_index()

    def _build_index(self) -> dict[str, list[Component]]:
        """Build a tag-based index for fast searching."""
        index = {}
        for component in self.components:
            for tag in component.tags:
                if tag not in index:
                    index[tag] = []
                index[tag].append(component)
            # Also index by category
            if component.category not in index:
                index[component.category] = []
            index[component.category].append(component)
        return index

    def search(self, query: str) -> list[Component]:
        """
        Search for components matching a query.

        Args:
            query: Search terms (space-separated)

        Returns:
            List of matching components, sorted by relevance
        """
        terms = query.lower().split()
        scores = {}

        for component in self.components:
            score = 0
            searchable = (
                component.name.lower() + " " +
                component.description.lower() + " " +
                " ".join(component.tags)
            )

            for term in terms:
                if term in searchable:
                    score += 1
                if term in component.tags:
                    score += 2  # Exact tag match is more relevant
                if term in component.name.lower():
                    score += 3  # Name match is most relevant

            if score > 0:
                scores[component.id] = score

        # Sort by score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [c for c in self.components if c.id in sorted_ids]

    def get_by_category(self, category: str) -> list[Component]:
        """Get all components in a category."""
        return [c for c in self.components if c.category == category]

    def get_by_id(self, component_id: str) -> Optional[Component]:
        """Get a specific component by ID."""
        for c in self.components:
            if c.id == component_id:
                return c
        return None

    def get_categories(self) -> list[str]:
        """Get all available categories."""
        return list(set(c.category for c in self.components))

    def format_for_prompt(self, components: list[Component]) -> str:
        """Format components for inclusion in an agent prompt."""
        if not components:
            return "No matching components found in the library."

        lines = ["## Available Components from Library\n"]
        lines.append("The following pre-approved components are available. **Use these instead of implementing from scratch:**\n")

        for c in components:
            lines.append(f"### {c.name} ({c.id})")
            lines.append(f"**Category:** {c.category}")
            lines.append(f"**Description:** {c.description}")
            if c.package:
                lines.append(f"**Package:** `{c.package}`")
            lines.append(f"**Tags:** {', '.join(c.tags)}")
            lines.append(f"\n**Usage:**\n```{c.language}\n{c.usage_example}\n```\n")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export library as JSON."""
        return json.dumps([c.to_dict() for c in self.components], indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ComponentLibrary":
        """Load library from JSON."""
        data = json.loads(json_str)
        components = [Component(**c) for c in data]
        return cls(components)
