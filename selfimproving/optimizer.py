"""Prompt optimization using Arize prompt-learning SDK."""

import os
import pandas as pd
from google import genai
from optimizer_sdk.prompt_learning_optimizer import PromptLearningOptimizer
from app_config import BASE_PROMPT, MODEL_NAME, OPTIMIZED_PROMPT_FILE
from google_provider import GoogleGenAIProvider


class PromptOptimizer:
    """Optimizes prompts using natural language feedback."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._log("""
============================================================
INITIALIZING PROMPT IMPROVEMENT SYSTEM
============================================================

Setting up connection to Google's AI model...
  - Model: """ + MODEL_NAME + """
  - This model will analyze feedback and suggest improvements
""")
        provider = GoogleGenAIProvider(verbose=False)  # Suppress provider's technical output

        self._log("""Configuring the learning system...
  - Current instructions: {:,} characters
  - The system will learn from reviewer feedback to improve these
""".format(len(BASE_PROMPT)))

        self.optimizer = PromptLearningOptimizer(
            prompt=BASE_PROMPT,
            model_choice=MODEL_NAME,
            provider=provider,
            verbose=False  # Suppress SDK's technical output
        )
        self._log("Ready to analyze feedback and improve instructions.\n")

    def _log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def optimize(self, feedback_df: pd.DataFrame) -> str:
        """Run optimization using collected feedback.

        Args:
            feedback_df: DataFrame with columns including 'response' and 'feedback'.

        Returns:
            Optimized prompt string.

        Raises:
            ValueError: If no feedback data is available.
        """
        if len(feedback_df) == 0:
            raise ValueError("No feedback data available for optimization")

        self._log(f"""
============================================================
WHAT'S HAPPENING
============================================================

We received feedback on {len(feedback_df)} contract review(s) where the AI's
analysis didn't meet expectations. We'll use this feedback to improve
how the AI reviews contracts.

WHY THIS MATTERS
Instead of manually rewriting instructions, we're using AI to learn
from its mistakes - similar to how an employee improves after feedback.

============================================================
FEEDBACK RECEIVED FROM REVIEWERS
============================================================
""")

        for idx, row in feedback_df.iterrows():
            contract_name = row.get('contract_file', 'Unknown contract')
            if '/' in str(contract_name):
                contract_name = contract_name.split('/')[-1]
            feedback_text = row.get('feedback', 'No details provided')
            if pd.isna(feedback_text):
                feedback_text = 'No details provided'
            self._log(f"  {idx + 1}. [{contract_name}]")
            self._log(f"     \"{feedback_text}\"\n")

        self._log("""
============================================================
IMPROVEMENT PROCESS
============================================================

The system will now:
  1. Package the feedback examples above
  2. Ask AI to identify patterns in what went wrong
  3. Generate improved contract review instructions
  4. Return the new instructions for your review

This typically takes 15-30 seconds...
""")

        optimized_prompt = self.optimizer.optimize(
            dataset=feedback_df,
            output_column='response',
            feedback_columns=['feedback']
        )

        char_diff = len(optimized_prompt) - len(BASE_PROMPT)
        diff_direction = "longer" if char_diff > 0 else "shorter" if char_diff < 0 else "same length"

        self._log(f"""
============================================================
IMPROVEMENT COMPLETE
============================================================

The AI has rewritten its contract review instructions based on the
feedback patterns it identified.

SUMMARY OF CHANGES
  Original instructions: {len(BASE_PROMPT):,} characters
  New instructions:      {len(optimized_prompt):,} characters
  Change:                {abs(char_diff):,} characters {diff_direction}

WHAT HAPPENS NEXT
  1. The new instructions will be compared against the current ones
  2. Both versions will be tested on sample contracts (if available)
  3. You'll see a side-by-side comparison to approve or reject

""")

        return optimized_prompt

    def get_current_prompt(self) -> str:
        """Get the current prompt (optimized if exists, else base).

        Returns:
            The current prompt text.
        """
        try:
            with open(OPTIMIZED_PROMPT_FILE, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return BASE_PROMPT

    @staticmethod
    def save_prompt(prompt: str) -> None:
        """Save a prompt to the optimized prompt file.

        Args:
            prompt: The prompt text to save.
        """
        with open(OPTIMIZED_PROMPT_FILE, 'w') as f:
            f.write(prompt)

    def build_meta_prompt(self, feedback_df: pd.DataFrame) -> str:
        """
        Build a representation of the meta-prompt for logging/explainability.

        This shows what information is being used to optimize the prompt.

        Args:
            feedback_df: DataFrame with feedback data.

        Returns:
            String representation of the meta-prompt.
        """
        meta_prompt = f"""META-PROMPT FOR OPTIMIZATION
{'=' * 60}

BASELINE PROMPT:
{'-' * 40}
{BASE_PROMPT}
{'-' * 40}

FEEDBACK EXAMPLES ({len(feedback_df)} total):
{'-' * 40}
"""
        for idx, row in feedback_df.iterrows():
            meta_prompt += f"\n--- Example {idx + 1} ---\n"
            if 'contract_file' in row:
                meta_prompt += f"Contract: {row['contract_file']}\n"
            if 'response' in row:
                response_preview = str(row['response'])[:500]
                meta_prompt += f"Model Output: {response_preview}...\n"
            if 'feedback' in row and pd.notna(row['feedback']):
                meta_prompt += f"User Feedback: {row['feedback']}\n"

        meta_prompt += f"""
{'-' * 40}

OPTIMIZATION INSTRUCTIONS:
{'-' * 40}
Based on the feedback above, generate an improved version of the baseline prompt that:
1. Addresses the issues identified in user feedback
2. Maintains the same output format (JSON with recommendation, reasoning, key_findings)
3. Preserves the {{contract_text}} template variable

{'=' * 60}
"""
        return meta_prompt

    def optimize_with_reasoning(self, feedback_df: pd.DataFrame, client: genai.Client) -> tuple:
        """
        Run optimization and generate explicit reasoning for the changes.

        Args:
            feedback_df: DataFrame with feedback data.
            client: Google GenAI client for generating reasoning.

        Returns:
            Tuple of (optimized_prompt: str, reasoning: str)
        """
        # First run the standard optimization
        optimized_prompt = self.optimize(feedback_df)

        # Get the current prompt for comparison
        current_prompt = self.get_current_prompt()

        # Now ask the LLM to explain the changes
        self._log("""
============================================================
GENERATING EXPLANATION
============================================================

Asking the AI to explain what it changed and why...
(This helps reviewers understand the reasoning behind the improvements)
""")

        reasoning_prompt = f"""You are analyzing changes made to a contract review prompt based on user feedback.

ORIGINAL PROMPT:
{'-' * 40}
{current_prompt}
{'-' * 40}

OPTIMIZED PROMPT:
{'-' * 40}
{optimized_prompt}
{'-' * 40}

USER FEEDBACK THAT TRIGGERED THESE CHANGES:
{'-' * 40}
"""
        for idx, row in feedback_df.iterrows():
            if 'feedback' in row and pd.notna(row['feedback']):
                reasoning_prompt += f"- {row['feedback']}\n"

        reasoning_prompt += f"""{'-' * 40}

Please explain:
1. What patterns did you identify in the user feedback?
2. What specific changes were made to the prompt?
3. How do these changes address the feedback?
4. What improvements should we expect to see?

Provide a clear, structured explanation."""

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=reasoning_prompt
            )
            reasoning = response.text
        except Exception as e:
            reasoning = f"Unable to generate reasoning: {str(e)}"

        return optimized_prompt, reasoning
