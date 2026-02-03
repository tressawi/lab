"""Feedback collection and storage for prompt optimization."""

import os
import pandas as pd
from datetime import datetime
from app_config import REVIEWS_FILE, DATA_DIR


class FeedbackCollector:
    """Collects and stores contract reviews with user feedback."""

    def __init__(self):
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create reviews file if it doesn't exist."""
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

        if not os.path.exists(REVIEWS_FILE):
            df = pd.DataFrame(columns=[
                'timestamp', 'contract_file', 'contract_text',
                'response', 'feedback'
            ])
            df.to_csv(REVIEWS_FILE, index=False)

    def record_review(self, contract_file: str, contract_text: str, response: str) -> int:
        """Record a review without feedback yet.

        Args:
            contract_file: Path to the contract file.
            contract_text: Full text of the contract.
            response: The agent's response/recommendation.

        Returns:
            Index of the new row.
        """
        df = pd.read_csv(REVIEWS_FILE)
        new_row = {
            'timestamp': datetime.now().isoformat(),
            'contract_file': contract_file,
            'contract_text': contract_text,
            'response': response,
            'feedback': ''  # Empty until user provides feedback
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(REVIEWS_FILE, index=False)
        return len(df) - 1

    def add_feedback(self, feedback: str):
        """Add feedback to the most recent review.

        Args:
            feedback: Natural language feedback about the review.

        Raises:
            ValueError: If there are no reviews to add feedback to.
        """
        df = pd.read_csv(REVIEWS_FILE)
        if len(df) == 0:
            raise ValueError("No reviews to add feedback to")
        df.loc[df.index[-1], 'feedback'] = feedback
        df.to_csv(REVIEWS_FILE, index=False)

    def get_feedback_data(self) -> pd.DataFrame:
        """Get all reviews with feedback for optimization.

        Returns:
            DataFrame containing only rows that have feedback.
        """
        df = pd.read_csv(REVIEWS_FILE)
        # Only return rows with non-empty feedback
        return df[df['feedback'].notna() & (df['feedback'] != '')]

    def get_review_count(self) -> int:
        """Get total number of reviews."""
        df = pd.read_csv(REVIEWS_FILE)
        return len(df)

    def get_feedback_count(self) -> int:
        """Get number of reviews with feedback."""
        return len(self.get_feedback_data())
