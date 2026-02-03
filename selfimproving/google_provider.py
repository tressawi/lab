"""Google Generative AI provider for the optimizer SDK."""

import os
from google import genai


class GoogleGenAIProvider:
    """Provider that uses Google's Generative AI for optimization."""

    def __init__(self, api_key: str = None, verbose: bool = True):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.verbose = verbose
        if self.verbose:
            print("  [Provider] Initialized Google Generative AI provider")

    async def generate_text(self, messages: list, model: str) -> str:
        """Generate text using Google's Generative AI."""
        if self.verbose:
            print(f"\n  [Provider] Sending request to {model}...")
            print(f"  [Provider] Processing {len(messages)} message(s)")

        prompt = "\n".join(m["content"] for m in messages)

        if self.verbose:
            print(f"  [Provider] Prompt size: {len(prompt):,} characters")
            print("  [Provider] Waiting for model response...")

        response = self.client.models.generate_content(
            model=model,
            contents=prompt
        )

        result = response.text

        if self.verbose:
            print(f"  [Provider] Received response: {len(result):,} characters")

        return result
