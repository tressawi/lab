#!/usr/bin/env python3
"""
DevAI - AI Development Agent CLI

Usage:
    # Single agent mode
    devai --task "Add email validation" --type feature
    devai -t "Fix login bug" --type bugfix

    # Pipeline mode (Dev -> Test with approvals)
    devai --pipeline --task "Add user authentication"

    # Interactive mode
    devai --interactive

    # Or as a module
    python -m devai --task "..."
"""

import asyncio
import argparse
import sys
from pathlib import Path

from devai.agents.dev_agent import DevAgent
from devai.agents.test_agent import TestAgent
from devai.pipeline import DevTestPipeline


async def run_task(args: argparse.Namespace) -> int:
    """Run a single agent task."""
    agent = DevAgent(store_path=args.store)

    task_methods = {
        "feature": agent.implement_feature,
        "bugfix": agent.fix_bug,
        "refactor": agent.refactor,
        "review": agent.review_code,
        "explore": agent.explore,
    }

    print(f"\n{'='*60}")
    print(f"DevAI - {args.type.upper()} Task")
    print(f"Working directory: {args.dir}")
    print(f"{'='*60}\n")

    if args.type in task_methods:
        result = await task_methods[args.type](
            description=args.task,
            working_dir=args.dir,
            task_id=args.task_id
        )
    else:
        result = await agent.custom_task(
            description=args.task,
            working_dir=args.dir,
            task_id=args.task_id,
            resume=args.resume
        )

    # Display result
    print(f"\n{'='*60}")
    print(f"Task ID: {result.task_id}")
    if result.session_id:
        print(f"Session ID: {result.session_id}")
    print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"{'='*60}\n")

    if result.error:
        print(f"Error: {result.error}\n")
        return 1

    print(result.content)
    return 0


async def run_pipeline(args: argparse.Namespace) -> int:
    """
    Run the Dev -> Test pipeline with human approval gates.

    This demonstrates:
    1. Dev Agent implements the task
    2. Human reviews and approves Dev Agent's work
    3. Test Agent generates tests
    4. Human reviews and approves Test Agent's work
    """
    pipeline = DevTestPipeline(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - PIPELINE MODE")
    print(f"{'='*60}")
    print(f"Task: {args.task}")
    print(f"Type: {args.type}")
    print(f"Working directory: {args.dir}")
    print(f"Approvals: {'Required' if not args.auto_approve else 'Auto-approved'}")
    print(f"{'='*60}\n")

    print("Pipeline stages:")
    print("  1. Dev Agent   - Implement the task")
    print("  2. Dev Review  - Human approves code changes")
    print("  3. Test Agent  - Generate tests")
    print("  4. Test Review - Human approves tests")
    print()

    result = await pipeline.run(
        task=args.task,
        task_type=args.type,
        working_dir=args.dir,
        require_approvals=not args.auto_approve
    )

    if not result.success:
        print(f"\nPipeline failed at stage: {result.stage.value}")
        print(f"Error: {result.error}")
        return 1

    print("\nPipeline completed successfully!")
    return 0


async def run_interactive(args: argparse.Namespace) -> int:
    """Run in interactive mode with pipeline support."""
    dev_agent = DevAgent(store_path=args.store)
    pipeline = DevTestPipeline(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - Interactive Mode")
    print(f"{'='*60}")
    print(f"Working directory: {args.dir}")
    print()
    print("Commands:")
    print("  <task>           - Run task with Dev Agent only")
    print("  pipeline <task>  - Run Dev -> Test pipeline with approvals")
    print("  resume           - Continue the last session")
    print("  exit/quit        - Stop")
    print(f"{'='*60}\n")

    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            # Check for pipeline command
            if user_input.lower().startswith("pipeline "):
                task = user_input[9:].strip()
                if task:
                    print("\nStarting pipeline...\n")
                    result = await pipeline.run(
                        task=task,
                        working_dir=args.dir,
                        require_approvals=True
                    )
                    if not result.success:
                        print(f"\nPipeline failed: {result.error}")
                else:
                    print("Usage: pipeline <task description>")
                continue

            # Check for resume
            resume = user_input.lower() == "resume"
            if resume:
                task = input("Continue with task: ").strip()
                if not task:
                    print("No task provided.")
                    continue
            else:
                task = user_input

            print("\nWorking...\n")

            result = await dev_agent.custom_task(
                description=task,
                working_dir=args.dir,
                resume=resume
            )

            if result.error:
                print(f"\nError: {result.error}")
            else:
                print(f"\n{result.content}")
                print(f"\n[Task ID: {result.task_id}]")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break

        except EOFError:
            print("\nGoodbye!")
            break

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="DevAI - AI Development Agent with Multi-Agent Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single agent - implement a feature
  python main.py --type feature --task "Add user authentication"

  # Single agent - fix a bug
  python main.py --type bugfix --task "Login fails with special characters"

  # Pipeline mode - Dev Agent -> approval -> Test Agent -> approval
  python main.py --pipeline --task "Add email validation" --type feature

  # Pipeline with auto-approve (skip human approvals)
  python main.py --pipeline --task "Add logging" --auto-approve

  # Interactive mode
  python main.py --interactive

Pipeline Flow:
  1. Dev Agent implements the requested feature/fix
  2. Human reviews and approves the code changes
  3. Test Agent generates comprehensive tests
  4. Human reviews and approves the tests
  5. Pipeline complete
        """
    )

    parser.add_argument(
        "--task", "-t",
        help="Task description"
    )

    parser.add_argument(
        "--type",
        choices=["feature", "bugfix", "refactor", "review", "explore", "custom"],
        default="feature",
        help="Type of task (default: feature)"
    )

    parser.add_argument(
        "--dir", "-d",
        default=".",
        help="Working directory (default: current directory)"
    )

    parser.add_argument(
        "--task-id",
        help="Task ID for tracking (auto-generated if not provided)"
    )

    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume the last session"
    )

    parser.add_argument(
        "--pipeline", "-p",
        action="store_true",
        help="Run full Dev -> Test pipeline with approval gates"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all stages (skip human approval prompts)"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )

    parser.add_argument(
        "--store",
        default="./context_store",
        help="Path to context store (default: ./context_store)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.interactive and not args.task:
        parser.error("--task is required unless using --interactive mode")

    # Ensure working directory exists
    work_dir = Path(args.dir)
    if not work_dir.exists():
        print(f"Error: Working directory does not exist: {args.dir}")
        sys.exit(1)

    # Run appropriate mode
    if args.interactive:
        exit_code = asyncio.run(run_interactive(args))
    elif args.pipeline:
        exit_code = asyncio.run(run_pipeline(args))
    else:
        exit_code = asyncio.run(run_task(args))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
