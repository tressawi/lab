"""Contract review agent using optimized prompts."""

import json
import os
import re
from google import genai
from app_config import BASE_PROMPT, MODEL_NAME, OPTIMIZED_PROMPT_FILE


class ContractReviewer:
    """Reviews contracts and provides recommendations."""

    def __init__(self, client: genai.Client, verbose: bool = True):
        self.client = client
        self.model_name = MODEL_NAME
        self.verbose = verbose
        self.prompt_template = self._load_prompt()

    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _load_prompt(self) -> str:
        """Load optimized prompt if exists, else use base prompt."""
        try:
            with open(OPTIMIZED_PROMPT_FILE, 'r') as f:
                prompt = f.read()
                self._log(f"  [Reviewer] Loaded optimized prompt ({len(prompt):,} chars)")
                return prompt
        except FileNotFoundError:
            self._log("  [Reviewer] Using base prompt (no optimization yet)")
            return BASE_PROMPT

    def reload_prompt(self):
        """Reload prompt after optimization."""
        self._log("  [Reviewer] Reloading prompt...")
        self.prompt_template = self._load_prompt()

    def review(self, contract_text: str) -> dict:
        """Review a contract and return structured recommendation.

        Args:
            contract_text: The full text of the contract to review.

        Returns:
            Dictionary with recommendation, reasoning, key_findings,
            and optionally suggested_changes.
        """
        self._log("\n" + "-" * 40)
        self._log("CONTRACT REVIEW PROCESS")
        self._log("-" * 40)

        self._log(f"\n[Step 1] Preparing review request...")
        self._log(f"  - Contract length: {len(contract_text):,} characters")
        self._log(f"  - Using prompt: {'optimized' if os.path.exists(OPTIMIZED_PROMPT_FILE) else 'base'}")

        prompt = self.prompt_template.format(contract_text=contract_text)
        self._log(f"  - Full prompt size: {len(prompt):,} characters")

        self._log(f"\n[Step 2] Sending to {self.model_name}...")
        self._log("  - Waiting for model response...")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        self._log(f"  - Response received: {len(response.text):,} characters")

        # Extract JSON from response (handle markdown code blocks)
        response_text = response.text

        self._log("\n[Step 3] Parsing model response...")

        # Try to extract JSON from code blocks if present
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
        if json_match:
            self._log("  - Extracted JSON from markdown code block")
            response_text = json_match.group(1).strip()

        # Parse JSON response
        try:
            result = json.loads(response_text)
            self._log("  - JSON parsed successfully")
            self._log(f"  - Recommendation: {result.get('recommendation', 'N/A')}")
        except json.JSONDecodeError:
            self._log("  - [Warning] Failed to parse JSON, creating error response")
            # If JSON parsing fails, return a structured error response
            result = {
                "recommendation": "ERROR",
                "reasoning": f"Failed to parse response: {response_text[:200]}",
                "key_findings": [],
                "suggested_changes": []
            }

        self._log("-" * 40 + "\n")

        return result
