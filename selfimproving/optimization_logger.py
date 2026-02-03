"""Dual console/file logging for optimization process explainability."""

import os
from datetime import datetime
from rich.console import Console

from app_config import DATA_DIR


class OptimizationLogger:
    """Logs all optimization steps to console and file for full transparency."""

    def __init__(self):
        """Initialize logger with timestamped log file."""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_dir = os.path.join(DATA_DIR, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file = os.path.join(self.logs_dir, f"optimization_log_{self.timestamp}.txt")
        self.console = Console()

        # Write header to log file
        with open(self.log_file, 'w') as f:
            f.write(f"Optimization Log - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n")

    def log(self, step: str, message: str, detail: str = None):
        """
        Log to console (summary) and file (full detail).

        Args:
            step: Step identifier (e.g., "STEP 1", "EVAL:CURRENT:case_001")
            message: Short message for console output
            detail: Optional detailed information for log file only
        """
        # Console: short message with step label
        self.console.print(f"[bold cyan][{step}][/bold cyan] {message}")

        # File: full detail
        with open(self.log_file, 'a') as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"STEP: {step}\n")
            f.write(f"TIME: {datetime.now().isoformat()}\n")
            f.write(f"{'=' * 60}\n")
            f.write(f"{message}\n")
            if detail:
                f.write(f"\nDETAILS:\n{'-' * 40}\n{detail}\n{'-' * 40}\n")

    def log_section(self, title: str):
        """Log a section header to both console and file."""
        self.console.print(f"\n[bold yellow]{'=' * 50}[/bold yellow]")
        self.console.print(f"[bold yellow]{title}[/bold yellow]")
        self.console.print(f"[bold yellow]{'=' * 50}[/bold yellow]")

        with open(self.log_file, 'a') as f:
            f.write(f"\n\n{'#' * 60}\n")
            f.write(f"# {title}\n")
            f.write(f"{'#' * 60}\n")

    def get_log_path(self) -> str:
        """Return the path to the log file."""
        return self.log_file
