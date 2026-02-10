#!/usr/bin/env python3
"""
DevAI - AI Development Agent CLI

Usage:
    # Interactive mode (default)
    devai
    devai --dir /path/to/project

    # Use @agent mentions to select agents:
    #   > @test Generate comprehensive tests
    #   > @cyber Run a security audit
    #   > @dev Fix the login bug        (or just type without prefix)

    # One-shot mode
    devai --task "@test Generate tests" --dir /path/to/project
    devai --task "@cyber Security audit" --dir /path/to/project
    devai --task "Fix login bug" --type bugfix

    # Pipeline mode (Dev -> Test with approvals)
    devai --pipeline --task "Add user authentication"
"""

import asyncio
import argparse
import re
import sys
from pathlib import Path

from devai.agents.dev_agent import DevAgent
from devai.agents.test_agent import TestAgent
from devai.agents.cyber_agent import CyberAgent
from devai.agents.cicd_agent import CICDAgent, Environment
from devai.pipeline import DevTestPipeline, FullCICDPipeline


def parse_agent_mention(task: str) -> tuple[str, str]:
    """
    Parse @agent mention prefix from a task string.

    Supports @dev, @test, @cyber, @cicd. If no prefix, defaults to "dev".

    Args:
        task: The raw task string, possibly starting with @agent

    Returns:
        Tuple of (agent_name, remaining_task)
    """
    match = re.match(r"^@(dev|test|cyber|cicd)\s+", task, re.IGNORECASE)
    if match:
        agent = match.group(1).lower()
        remaining = task[match.end():].strip()
        return agent, remaining
    return "dev", task


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


async def run_test_task(args: argparse.Namespace, task: str) -> int:
    """Run a standalone test agent task."""
    agent = TestAgent(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - TEST AGENT")
    print(f"Working directory: {args.dir}")
    print(f"{'='*60}\n")

    result = await agent.explore_and_test(
        description=task,
        working_dir=args.dir,
        task_id=args.task_id
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


async def run_cyber_task(args: argparse.Namespace, task: str) -> int:
    """Run a standalone cyber agent task."""
    agent = CyberAgent(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - CYBER AGENT")
    print(f"Working directory: {args.dir}")
    print(f"{'='*60}\n")

    result = await agent.full_scan(
        description=task,
        working_dir=args.dir,
        task_id=args.task_id
    )

    # Display result
    print(f"\n{'='*60}")
    print(f"Task ID: {result.task_id}")
    if result.session_id:
        print(f"Session ID: {result.session_id}")
    print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")

    # Parse and display security decision
    if result.success:
        decision, blockers = agent.parse_decision(result)
        print(f"Security Decision: {decision}")
        if blockers:
            for blocker in blockers:
                print(f"  - {blocker}")

    print(f"{'='*60}\n")

    if result.error:
        print(f"Error: {result.error}\n")
        return 1

    print(result.content)
    return 0


async def run_cicd_task(args: argparse.Namespace, task: str) -> int:
    """Run a standalone CI/CD agent task."""
    agent = CICDAgent(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - CI/CD AGENT")
    print(f"Working directory: {args.dir}")
    print(f"{'='*60}\n")

    result = await agent.run(
        task=task,
        working_dir=args.dir,
        task_id=args.task_id
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
    # Use FullCICDPipeline if deploying, otherwise use DevTestPipeline
    if hasattr(args, 'deploy') and args.deploy:
        pipeline = FullCICDPipeline(store_path=args.store)
    else:
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
    if hasattr(args, 'deploy') and args.deploy:
        print("  5. Cyber Agent - Security scan")
        print("  6. Security Gate - BLOCK/WARN/APPROVE")
        print("  7. Build      - Jenkins build (if configured)")
        print("  8. Deploy     - Deploy to environments")
    print()

    # Build deploy_to list from args
    deploy_to = None
    if hasattr(args, 'deploy') and args.deploy:
        if args.deploy == "all":
            deploy_to = ["dev", "staging", "prod"]
        else:
            deploy_to = [args.deploy]

    # Get jenkins job if specified
    jenkins_job = getattr(args, 'jenkins_job', None)

    if deploy_to:
        result = await pipeline.run(
            task=args.task,
            task_type=args.type,
            working_dir=args.dir,
            require_approvals=not args.auto_approve,
            deploy_to=deploy_to,
            jenkins_job=jenkins_job
        )
    else:
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
    """Run in interactive mode with @agent mention support."""
    dev_agent = DevAgent(store_path=args.store)
    test_agent = TestAgent(store_path=args.store)
    cyber_agent = CyberAgent(store_path=args.store)
    cicd_agent = CICDAgent(store_path=args.store)
    pipeline = DevTestPipeline(store_path=args.store)

    print(f"\n{'='*60}")
    print("DevAI - Interactive Mode")
    print(f"{'='*60}")
    print(f"Working directory: {args.dir}")
    print()
    print("Agents:  @dev (default)  @test  @cyber  @cicd")
    print()
    print("Commands:")
    print("  @test <task>     - Run task with Test Agent")
    print("  @cyber <task>    - Run task with Cyber Agent")
    print("  @cicd <task>     - Run task with CI/CD Agent")
    print("  @dev <task>      - Run task with Dev Agent")
    print("  <task>           - Run task with Dev Agent (default)")
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
                agent_name = "dev"
            else:
                agent_name, task = parse_agent_mention(user_input)

            print(f"\n[{agent_name}] Working...\n")

            if agent_name == "test":
                result = await test_agent.explore_and_test(
                    description=task,
                    working_dir=args.dir
                )
            elif agent_name == "cyber":
                result = await cyber_agent.full_scan(
                    description=task,
                    working_dir=args.dir
                )
            elif agent_name == "cicd":
                result = await cicd_agent.run(
                    task=task,
                    working_dir=args.dir
                )
            else:
                result = await dev_agent.custom_task(
                    description=task,
                    working_dir=args.dir,
                    resume=resume
                )

            if result.error:
                print(f"\nError: {result.error}")
            else:
                print(f"\n{result.content}")
                # Show security decision for cyber agent
                if agent_name == "cyber" and result.success:
                    decision, blockers = cyber_agent.parse_decision(result)
                    print(f"\nSecurity Decision: {decision}")
                    if blockers:
                        for blocker in blockers:
                            print(f"  - {blocker}")
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
  # Interactive mode (default - just run devai)
  devai
  devai --dir /path/to/project

  # In interactive mode, use @agent mentions:
  #   > @test Generate comprehensive tests
  #   > @cyber Run a security audit
  #   > @cicd Deploy to staging
  #   > @dev Fix the login bug
  #   > Fix the login bug              (defaults to @dev)

  # One-shot mode with @agent mentions
  devai --task "@test Generate tests" --dir /path/to/project
  devai --task "@cyber Security audit" --dir /path/to/project
  devai --task "@cicd Trigger build" --dir /path/to/project
  devai --task "Add feature" --type feature

  # Pipeline mode - Dev -> approval -> Test -> approval
  devai --pipeline --task "Add email validation" --type feature
  devai --pipeline --task "Add logging" --auto-approve

  # Full CI/CD Pipeline - includes build and deployment
  devai --pipeline --task "Add feature" --deploy staging
  devai --pipeline --task "Release v1.2" --deploy prod --jenkins-job my-app-build

  # Rollback
  devai --task "@cicd Rollback to 1.0.141" --deploy prod --artifact-version 1.0.141
        """
    )

    parser.add_argument(
        "--task", "-t",
        help="Task description (prefix with @test or @cyber to select agent)"
    )

    parser.add_argument(
        "--type",
        choices=["feature", "bugfix", "refactor", "review", "explore", "custom"],
        default="feature",
        help="Type of task for dev agent (default: feature)"
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
        help="Run in interactive mode (this is the default when no --task is given)"
    )

    parser.add_argument(
        "--store",
        default="./context_store",
        help="Path to context store (default: ./context_store)"
    )

    # CI/CD arguments
    parser.add_argument(
        "--deploy",
        choices=["dev", "staging", "prod", "all"],
        help="Deploy after successful pipeline (requires --pipeline)"
    )

    parser.add_argument(
        "--jenkins-job",
        help="Jenkins job name to trigger"
    )

    parser.add_argument(
        "--artifact-version",
        help="Specific artifact version to deploy"
    )

    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to previous version (use with --deploy and --artifact-version)"
    )

    args = parser.parse_args()

    # Pipeline mode requires --task
    if args.pipeline and not args.task:
        parser.error("--task is required for pipeline mode")

    # Ensure working directory exists
    work_dir = Path(args.dir)
    if not work_dir.exists():
        print(f"Error: Working directory does not exist: {args.dir}")
        sys.exit(1)

    # Run appropriate mode
    if args.pipeline:
        exit_code = asyncio.run(run_pipeline(args))
    elif args.task:
        # One-shot mode: parse @agent mention from task
        agent_name, task = parse_agent_mention(args.task)
        if agent_name == "test":
            exit_code = asyncio.run(run_test_task(args, task))
        elif agent_name == "cyber":
            exit_code = asyncio.run(run_cyber_task(args, task))
        elif agent_name == "cicd":
            exit_code = asyncio.run(run_cicd_task(args, task))
        else:
            exit_code = asyncio.run(run_task(args))
    else:
        # Default: interactive mode
        exit_code = asyncio.run(run_interactive(args))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
