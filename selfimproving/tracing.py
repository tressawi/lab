"""Phoenix tracing setup for LLM observability."""

import phoenix as px
from phoenix.otel import register
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

PROJECT_NAME = "self-improving-agent"


def init_tracing():
    """Initialize Phoenix tracing for LLM observability.

    Returns:
        Phoenix session object with URL for the tracing UI, or a mock object if startup fails.
    """
    # Launch Phoenix locally (non-blocking)
    session = px.launch_app()

    # Handle case where Phoenix fails to start
    if session is None:
        print("Warning: Phoenix failed to start. Traces will not be collected.")
        print("Make sure ports 6006 and 4317 are not in use.")

        class MockSession:
            url = "http://localhost:6006 (not running)"
        session = MockSession()
    else:
        print(f"Phoenix UI available at: {session.url}")

    # Register the tracer provider with a project name
    tracer_provider = register(
        project_name=PROJECT_NAME,
        endpoint="http://localhost:6006/v1/traces"
    )

    # Instrument Google Generative AI calls
    GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

    print(f"Project: {PROJECT_NAME}")
    return session
