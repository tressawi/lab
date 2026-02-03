#!/usr/bin/env python3
"""Self-Improving Contract Review Agent CLI.

A demo of Prompt Learning - using natural language feedback to improve LLM prompts.
"""

import os
import sys
import webbrowser
from dotenv import load_dotenv
from google import genai

from rich.console import Console

from tracing import init_tracing
from contract_reviewer import ContractReviewer
from feedback_collector import FeedbackCollector
from optimizer import PromptOptimizer
from diff_panel import DiffPanel, UserChoice
from app_config import OPTIMIZED_PROMPT_FILE, BASE_PROMPT, CONTRACTS_DIR, GOLDEN_DATASET_FILE
from optimization_logger import OptimizationLogger
from evaluator import PromptEvaluator


def print_banner():
    """Print welcome banner."""
    print()
    print("=" * 60)
    print("  Self-Improving Contract Review Agent")
    print("  Using Arize prompt-learning + Phoenix")
    print("=" * 60)


def print_help():
    """Print available commands."""
    print("\nCommands:")
    print("  review <file>  - Review a contract file")
    print("  contracts      - List available contract files")
    print("  feedback       - Provide feedback on the last review")
    print("  optimize       - Run optimization with collected feedback")
    print("  show-prompt    - Show current prompt")
    print("  traces         - Open Phoenix tracing UI in browser")
    print("  status         - Show review/feedback counts")
    print("  reset          - Reset to base prompt")
    print("  help           - Show this help message")
    print("  quit           - Exit the program")
    print()


def main():
    """Main CLI loop."""
    # Load environment variables
    load_dotenv()

    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not set.")
        print("Please set it in your environment or create a .env file.")
        sys.exit(1)

    print_banner()

    # Initialize Phoenix tracing BEFORE creating the client
    print("\nInitializing Phoenix tracing...")
    session = init_tracing()

    # Create Gemini client AFTER instrumentation
    client = genai.Client(api_key=api_key)

    # Initialize components
    print("Loading contract reviewer...")
    reviewer = ContractReviewer(client)
    feedback_collector = FeedbackCollector()
    optimizer = PromptOptimizer()
    console = Console()
    diff_panel = DiffPanel(console)

    print_help()
    print(f"Phoenix UI: {session.url}")
    print()

    while True:
        try:
            cmd = input("> ").strip()

            if not cmd:
                continue

            # Review command
            if cmd.startswith("review "):
                filepath = cmd[7:].strip()
                if not os.path.exists(filepath):
                    print(f"Error: File not found: {filepath}")
                    continue

                with open(filepath, 'r') as f:
                    contract_text = f.read()

                print("\nAnalyzing contract...")
                result = reviewer.review(contract_text)

                # Display result
                print(f"\nRECOMMENDATION: {result.get('recommendation', 'N/A')}")
                print(f"\nReasoning: {result.get('reasoning', 'N/A')}")

                if result.get('key_findings'):
                    print("\nKey findings:")
                    for finding in result['key_findings']:
                        print(f"  - {finding}")

                if result.get('suggested_changes'):
                    print("\nSuggested changes:")
                    for change in result['suggested_changes']:
                        print(f"  - {change}")

                # Record review
                feedback_collector.record_review(
                    filepath, contract_text, str(result)
                )

                # Prompt for feedback
                print("\nHow was this review?")
                print("  1. Approve")
                print("  2. Reject (requires feedback)")
                print("  3. Provide feedback")
                choice = input("Choice [1/2/3]: ").strip()

                if choice == "1":
                    print("Review approved.")
                elif choice == "2":
                    feedback = input("What was wrong with this review? ").strip()
                    if feedback:
                        feedback_collector.add_feedback(feedback)
                        print("Feedback recorded. Run 'optimize' to improve the prompt.")
                    else:
                        print("Rejection requires feedback. No feedback recorded.")
                elif choice == "3":
                    feedback = input("Feedback: ").strip()
                    if feedback:
                        feedback_collector.add_feedback(feedback)
                        print("Feedback recorded. Run 'optimize' to improve the prompt.")
                    else:
                        print("No feedback provided.")

            # Feedback command
            elif cmd == "feedback":
                print("Enter your feedback (what did the agent miss or get wrong?):")
                feedback = input("Feedback: ").strip()
                if feedback:
                    feedback_collector.add_feedback(feedback)
                    print("Feedback recorded. Run 'optimize' to improve the prompt.")
                else:
                    print("No feedback provided.")

            # Optimize command
            elif cmd == "optimize":
                # Initialize logger for full explainability
                logger = OptimizationLogger()
                logger.log_section("SELF-IMPROVEMENT PROCESS STARTING")
                logger.log("START", "Optimization process initiated")

                # Step 1: Collect feedback
                logger.log("STEP 1", "Collecting feedback data...")
                feedback_df = feedback_collector.get_feedback_data()
                count = len(feedback_df)

                if count == 0:
                    logger.log("STEP 1", "No feedback available",
                              detail="Review some contracts and provide feedback first.")
                    console.print("  [yellow]No feedback available.[/yellow]")
                    console.print("  Review some contracts and provide feedback first.")
                    continue

                logger.log("STEP 1", f"Found {count} feedback example(s)",
                          detail=feedback_df.to_string())

                # Step 2: Analyze feedback
                logger.log("STEP 2", "Analyzing feedback patterns...")
                for idx, row in feedback_df.iterrows():
                    logger.log(f"STEP 2:FEEDBACK:{idx+1}", f"Feedback #{idx+1}",
                              detail=f"Contract: {row.get('contract_file', 'N/A')}\n"
                                     f"Response: {str(row.get('response', 'N/A'))[:500]}...\n"
                                     f"Feedback: {row.get('feedback', 'N/A')}")

                try:
                    # Step 3: Show meta-prompt
                    logger.log("STEP 3", "Initializing optimizer...")
                    optimizer = PromptOptimizer(verbose=True)

                    meta_prompt = optimizer.build_meta_prompt(feedback_df)
                    logger.log("STEP 3:META_PROMPT", "Full meta-prompt being used for optimization",
                              detail=meta_prompt)

                    # Step 4: Run optimization with reasoning
                    logger.log("STEP 4", "Running LLM optimization...")
                    current_prompt = optimizer.get_current_prompt()

                    optimized_prompt, reasoning = optimizer.optimize_with_reasoning(feedback_df, client)

                    logger.log("STEP 4:REASONING", "LLM explanation of changes",
                              detail=reasoning)
                    logger.log("STEP 4:RESULT", "Generated optimized prompt",
                              detail=optimized_prompt)

                    # Step 5: Evaluate both prompts against golden dataset
                    logger.log_section("GOLDEN DATASET EVALUATION")
                    logger.log("STEP 5", "Evaluating prompts against golden dataset...")

                    if os.path.exists(GOLDEN_DATASET_FILE):
                        evaluator = PromptEvaluator(client, logger)
                        comparison = evaluator.compare_prompts(current_prompt, optimized_prompt)

                        old_results = comparison['old']
                        new_results = comparison['new']
                        improvement = comparison['improvement']
                    else:
                        logger.log("STEP 5", "No golden dataset found - skipping evaluation",
                                  detail=f"Expected file at: {GOLDEN_DATASET_FILE}")
                        old_results = None
                        new_results = None
                        improvement = None

                    # Step 6: Print Jira ticket
                    logger.log_section("JIRA TICKET CREATION")
                    logger.log("STEP 6", "Creating Jira ticket...")

                    feedback_list = feedback_df['feedback'].dropna().tolist()

                    jira_ticket = f"""
================================================================================
JIRA TICKET: Prompt Optimization
================================================================================
Title: Prompt optimization based on {len(feedback_df)} feedback items

Description:
  Feedback analyzed:
"""
                    for fb in feedback_list:
                        jira_ticket += f"    - {fb}\n"

                    jira_ticket += f"""
AI Reasoning for Changes:
{reasoning}

"""
                    if old_results and new_results:
                        jira_ticket += f"""Evaluation Results:
  CURRENT:  Accuracy={old_results['accuracy']:.0%}, Coverage={old_results['coverage']:.0%}, Format={old_results['format_compliance']:.0%}
  PROPOSED: Accuracy={new_results['accuracy']:.0%}, Coverage={new_results['coverage']:.0%}, Format={new_results['format_compliance']:.0%}
  IMPROVEMENT: Accuracy={improvement['accuracy_delta']:+.0%}, Coverage={improvement['coverage_delta']:+.0%}

"""
                    else:
                        jira_ticket += "Evaluation Results: N/A (no golden dataset)\n\n"

                    jira_ticket += f"""Prompt Diff:
  Original length: {len(current_prompt):,} characters
  New length: {len(optimized_prompt):,} characters
  Change: {len(optimized_prompt) - len(current_prompt):+,} characters
================================================================================
"""
                    console.print(jira_ticket)
                    logger.log("STEP 6:TICKET", "Jira ticket content", detail=jira_ticket)

                    # Step 7: Show diff and get user decision
                    logger.log("STEP 7", "Showing diff for user decision...")
                    choice, final_prompt = diff_panel.show_and_confirm(
                        current_prompt,
                        optimized_prompt
                    )

                    logger.log("STEP 7:CHOICE", f"User chose: {choice.name}")

                    if choice == UserChoice.ACCEPT:
                        PromptOptimizer.save_prompt(final_prompt)
                        console.print("\n[green]Optimized prompt saved![/green]")
                        reviewer.reload_prompt()
                        console.print("  Prompt reloaded successfully!")
                        logger.log("COMPLETE", "Optimization accepted and applied")

                    elif choice == UserChoice.REJECT:
                        console.print("\n[yellow]Changes discarded.[/yellow]")
                        console.print("The current prompt remains unchanged.")
                        logger.log("COMPLETE", "Optimization rejected - no changes applied")

                    elif choice == UserChoice.MODIFY:
                        PromptOptimizer.save_prompt(final_prompt)
                        console.print("\n[green]Your modified prompt saved![/green]")
                        reviewer.reload_prompt()
                        console.print("  Prompt reloaded successfully!")
                        logger.log("COMPLETE", "User modified prompt applied",
                                  detail=final_prompt)

                    console.print(f"\n[dim]Full optimization log: {logger.get_log_path()}[/dim]")

                except Exception as e:
                    logger.log("ERROR", f"Optimization failed: {e}")
                    console.print(f"\n[red][Error] Optimization failed: {e}[/red]")
                    console.print(f"[dim]See log for details: {logger.get_log_path()}[/dim]")

            # Show prompt command
            elif cmd == "show-prompt":
                try:
                    with open(OPTIMIZED_PROMPT_FILE, 'r') as f:
                        print("\n--- Current Optimized Prompt ---")
                        print(f.read())
                        print("--- End of Prompt ---")
                except FileNotFoundError:
                    print("\n--- Base Prompt (no optimization yet) ---")
                    print(BASE_PROMPT)
                    print("--- End of Prompt ---")

            # Traces command
            elif cmd == "traces":
                print(f"Opening Phoenix UI: {session.url}")
                webbrowser.open(session.url)

            # Status command
            elif cmd == "status":
                total = feedback_collector.get_review_count()
                with_feedback = feedback_collector.get_feedback_count()
                has_optimized = os.path.exists(OPTIMIZED_PROMPT_FILE)
                print(f"\nTotal reviews: {total}")
                print(f"Reviews with feedback: {with_feedback}")
                print(f"Prompt optimized: {'Yes' if has_optimized else 'No'}")

            # List contracts command
            elif cmd == "contracts":
                if not os.path.exists(CONTRACTS_DIR):
                    print(f"Contracts directory not found: {CONTRACTS_DIR}")
                    continue
                files = [f for f in os.listdir(CONTRACTS_DIR) if f.endswith('.txt')]
                if not files:
                    print("No contract files found.")
                else:
                    print("\nAvailable contracts:")
                    for f in sorted(files):
                        print(f"  {CONTRACTS_DIR}/{f}")

            # Reset command
            elif cmd == "reset":
                try:
                    os.remove(OPTIMIZED_PROMPT_FILE)
                    print("Optimized prompt removed.")
                except FileNotFoundError:
                    print("No optimized prompt to remove.")
                reviewer.reload_prompt()
                print("Reset to base prompt.")

            # Help command
            elif cmd == "help":
                print_help()

            # Quit command
            elif cmd in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
