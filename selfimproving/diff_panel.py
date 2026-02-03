"""Diff panel for reviewing prompt optimization changes."""

import os
import difflib
import tempfile
import subprocess
from enum import Enum
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


class UserChoice(Enum):
    """User's decision on the optimized prompt."""
    ACCEPT = "accept"
    REJECT = "reject"
    MODIFY = "modify"


class DiffPanel:
    """Displays diff between prompts and handles user interaction."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def generate_unified_diff(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "Current Prompt",
        new_label: str = "Optimized Prompt"
    ) -> str:
        """Generate a unified diff string between two texts."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        # Ensure last lines end with newline for clean diff
        if old_lines and not old_lines[-1].endswith('\n'):
            old_lines[-1] += '\n'
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_label,
            tofile=new_label,
            lineterm=""
        )
        return "".join(diff)

    def display_diff(self, old_text: str, new_text: str) -> bool:
        """Display a colored diff panel using rich.

        Returns:
            True if there are changes, False if no changes detected.
        """
        diff_text = self.generate_unified_diff(old_text, new_text)

        if not diff_text.strip():
            self.console.print(
                Panel("[yellow]No changes detected[/yellow]",
                      title="Diff")
            )
            return False

        # Color the diff output
        colored_diff = self._colorize_diff(diff_text)

        self.console.print(Panel(
            colored_diff,
            title="[bold]Prompt Changes[/bold]",
            subtitle="[dim]unified diff[/dim]",
            border_style="blue"
        ))
        return True

    def _colorize_diff(self, diff_text: str) -> Text:
        """Apply git-style colors to diff lines."""
        text = Text()
        for line in diff_text.split("\n"):
            if line.startswith("+++"):
                text.append(line + "\n", style="bold green")
            elif line.startswith("---"):
                text.append(line + "\n", style="bold red")
            elif line.startswith("@@"):
                text.append(line + "\n", style="cyan")
            elif line.startswith("+"):
                text.append(line + "\n", style="green")
            elif line.startswith("-"):
                text.append(line + "\n", style="red")
            else:
                text.append(line + "\n")
        return text

    def prompt_user_choice(self) -> UserChoice:
        """Display Accept/Reject/Modify menu and get user choice."""
        self.console.print()
        self.console.print("[bold]What would you like to do?[/bold]")
        self.console.print("  [green]A[/green]ccept  - Save the optimized prompt")
        self.console.print("  [red]R[/red]eject  - Discard changes, keep current prompt")
        self.console.print("  [yellow]M[/yellow]odify  - Edit the optimized prompt in your editor")
        self.console.print()

        while True:
            choice = Prompt.ask(
                "Choice",
                choices=["a", "accept", "r", "reject", "m", "modify"],
                default="a"
            ).lower()

            if choice in ("a", "accept"):
                return UserChoice.ACCEPT
            elif choice in ("r", "reject"):
                return UserChoice.REJECT
            elif choice in ("m", "modify"):
                return UserChoice.MODIFY

    def open_in_editor(self, text: str) -> Optional[str]:
        """Open text in user's $EDITOR and return edited content."""
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))

        # Create a temporary file with the prompt content
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="prompt_edit_",
            delete=False
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        try:
            # Open editor and wait for it to close
            self.console.print(f"[dim]Opening {editor}...[/dim]")
            result = subprocess.run([editor, tmp_path])

            if result.returncode != 0:
                self.console.print(
                    f"[red]Editor exited with code {result.returncode}[/red]"
                )
                return None

            # Read back the edited content
            with open(tmp_path, "r") as f:
                edited_text = f.read()

            return edited_text

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def show_and_confirm(
        self,
        old_prompt: str,
        new_prompt: str
    ) -> Tuple[UserChoice, Optional[str]]:
        """
        Main entry point: show diff and get user decision.

        Returns:
            Tuple of (UserChoice, final_prompt_or_None)
            - ACCEPT: (ACCEPT, new_prompt)
            - REJECT: (REJECT, None)
            - MODIFY: (MODIFY, edited_prompt)
        """
        has_changes = self.display_diff(old_prompt, new_prompt)

        if not has_changes:
            self.console.print("[yellow]No optimization needed.[/yellow]")
            return (UserChoice.REJECT, None)

        choice = self.prompt_user_choice()

        if choice == UserChoice.ACCEPT:
            return (choice, new_prompt)
        elif choice == UserChoice.REJECT:
            return (choice, None)
        elif choice == UserChoice.MODIFY:
            edited = self.open_in_editor(new_prompt)
            if edited is None:
                # Editor failed, fall back to reject
                self.console.print("[yellow]Edit cancelled, keeping current prompt[/yellow]")
                return (UserChoice.REJECT, None)

            # Show diff of modifications if user made changes
            if edited.strip() != new_prompt.strip():
                self.console.print("\n[bold]Your modifications:[/bold]")
                self.display_diff(new_prompt, edited)

            return (choice, edited)
