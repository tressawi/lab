"""Configuration and prompts for the contract review agent."""

import os

# Base prompt (before any optimization)
BASE_PROMPT = """
You are a contract review specialist. Analyze the following contract and provide:

1. RECOMMENDATION: One of APPROVE, MODIFY, or REJECT
2. REASONING: Brief explanation of your recommendation
3. KEY_FINDINGS: List of important clauses or issues found

Contract to review:
{contract_text}

Respond in JSON format:
{{
  "recommendation": "APPROVE|MODIFY|REJECT",
  "reasoning": "...",
  "key_findings": ["...", "..."],
  "suggested_changes": ["..."]
}}
"""

# Model configuration
MODEL_NAME = "gemini-2.0-flash"

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.csv")
OPTIMIZED_PROMPT_FILE = os.path.join(DATA_DIR, "optimized_prompt.txt")
CONTRACTS_DIR = os.path.join(BASE_DIR, "sample_contracts")
GOLDEN_DATASET_FILE = os.path.join(DATA_DIR, "golden_dataset.csv")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
