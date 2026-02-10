"""Pipeline orchestration for multi-agent workflows with approval gates."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .agents.dev_agent import DevAgent
from .agents.test_agent import TestAgent
from .agents.cyber_agent import CyberAgent
from .agents.base import AgentResult
from .approval import ApprovalGate, require_approval, ApprovalStatus
from .shared_context.store import ContextStore


class PipelineStage(Enum):
    """Stages in the development pipeline."""
    DESIGN = "design"
    DESIGN_APPROVAL = "design_approval"
    DEV = "dev"
    DEV_APPROVAL = "dev_approval"
    TEST = "test"
    TEST_APPROVAL = "test_approval"
    CYBER = "cyber"
    CYBER_APPROVAL = "cyber_approval"
    # CI/CD stages
    BUILD = "build"
    ARTIFACT_UPLOAD = "artifact_upload"
    DEPLOY_DEV = "deploy_dev"
    DEPLOY_STAGING = "deploy_staging"
    DEPLOY_STAGING_APPROVAL = "deploy_staging_approval"
    DEPLOY_PROD = "deploy_prod"
    DEPLOY_PROD_APPROVAL = "deploy_prod_approval"
    # Terminal stages
    BLOCKED = "blocked"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """Result from a pipeline execution."""
    pipeline_id: str
    stage: PipelineStage
    design_result: Optional[AgentResult] = None
    dev_result: Optional[AgentResult] = None
    test_result: Optional[AgentResult] = None
    cyber_result: Optional[AgentResult] = None
    security_decision: Optional[str] = None  # BLOCK, WARN, APPROVE
    security_blockers: list[str] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None
    # CI/CD results
    cicd_result: Optional[AgentResult] = None
    build_number: Optional[int] = None
    artifact_version: Optional[str] = None
    artifact_sha256: Optional[str] = None
    deployment_results: dict = field(default_factory=dict)  # {env: result}


class DevTestCyberPipeline:
    """
    Orchestrates Design -> Dev -> Test -> Cyber workflow with human approval gates.

    Flow:
    1. Dev Agent creates design document (checks component library)
    2. Human approves design before implementation
    3. Dev Agent implements feature/fix (following approved design)
    4. Human approves Dev Agent's work
    5. Test Agent generates tests
    6. Human approves Test Agent's work
    7. Cyber Agent scans for security issues
    8. Cyber decision: APPROVE/WARN/BLOCK
       - BLOCK: Pipeline stops, security issues must be fixed
       - WARN: Human reviews and decides
       - APPROVE: Pipeline continues
    9. Pipeline complete
    """

    def __init__(self, store_path: str = "./context_store"):
        self.store_path = store_path
        self.dev_agent = DevAgent(store_path=store_path)
        self.test_agent = TestAgent(store_path=store_path)
        self.cyber_agent = CyberAgent(store_path=store_path)
        self.approval_gate = ApprovalGate(store_path=store_path)
        self.context_store = ContextStore(store_path=store_path)

    async def run(
        self,
        task: str,
        task_type: str = "feature",
        working_dir: str = ".",
        require_approvals: bool = True,
        skip_design: bool = False
    ) -> PipelineResult:
        """
        Run the full Design -> Dev -> Test -> Cyber pipeline.

        Args:
            task: Task description
            task_type: Type of task (feature, bugfix, refactor)
            working_dir: Directory to work in
            require_approvals: Whether to require human approvals
            skip_design: Skip design phase (for bugfixes/small changes)

        Returns:
            PipelineResult with outcomes from all stages
        """
        pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"

        result = PipelineResult(
            pipeline_id=pipeline_id,
            stage=PipelineStage.DESIGN
        )

        print(f"\n{'='*60}")
        print(f"PIPELINE: {pipeline_id}")
        print(f"Task: {task}")
        print(f"Type: {task_type}")
        print(f"{'='*60}\n")

        print("Pipeline stages:")
        print("  1. Design      - Create design document (check component library)")
        print("  2. Design Review - Human approves design before coding")
        print("  3. Dev Agent   - Implement following approved design")
        print("  4. Dev Review  - Human approves code changes")
        print("  5. Test Agent  - Generate tests")
        print("  6. Test Review - Human approves tests")
        print("  7. Cyber Agent - Security scan")
        print("  8. Security Gate - BLOCK/WARN/APPROVE")
        print()

        # Track approved design for implementation phase
        approved_design = None

        # ============================================================
        # Stage 1: Design (for features, can be skipped for bugfixes)
        # ============================================================
        if task_type == "feature" and not skip_design:
            print("\n[STAGE 1/8] Design - Creating design document...")
            print("-" * 40)

            try:
                design_result = await self.dev_agent.create_design(
                    task, working_dir, task_id=f"{pipeline_id}-design"
                )

                result.design_result = design_result

                if not design_result.success:
                    result.stage = PipelineStage.FAILED
                    result.success = False
                    result.error = f"Design phase failed: {design_result.error}"
                    return result

                print(f"\nDesign Document:\n{design_result.content[:800]}...")

            except Exception as e:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Design phase error: {str(e)}"
                return result

            # ============================================================
            # Stage 2: Design Approval
            # ============================================================
            result.stage = PipelineStage.DESIGN_APPROVAL

            if require_approvals:
                print("\n[STAGE 2/8] Design Approval - Human Review Required")
                print("-" * 40)
                print("\nReview the design document above.")
                print("The design must be approved before implementation begins.")

                try:
                    approval = await require_approval(
                        self.approval_gate,
                        agent="dev",
                        action="design_approval",
                        description=f"Design document for: {task}",
                        details={
                            "task_id": design_result.task_id,
                            "design_summary": design_result.content[:500] + "..." if len(design_result.content) > 500 else design_result.content
                        }
                    )
                    result.approvals.append(approval.to_dict())
                    approved_design = design_result.content
                    print("\nDesign APPROVED - proceeding to implementation.")

                except PermissionError as e:
                    result.stage = PipelineStage.FAILED
                    result.success = False
                    result.error = f"Design rejected: {str(e)}"
                    return result
            else:
                print("\n[STAGE 2/8] Design Approval - Skipped (auto-approve mode)")
                approved_design = design_result.content
        else:
            print("\n[STAGE 1-2/8] Design Phase - Skipped (not a feature or skip_design=True)")

        # ============================================================
        # Stage 3: Dev Agent
        # ============================================================
        result.stage = PipelineStage.DEV
        print("\n[STAGE 3/8] Dev Agent - Implementing...")
        print("-" * 40)

        try:
            if task_type == "feature":
                dev_result = await self.dev_agent.implement_feature(
                    task, working_dir, task_id=f"{pipeline_id}-dev",
                    approved_design=approved_design
                )
            elif task_type == "bugfix":
                dev_result = await self.dev_agent.fix_bug(
                    task, working_dir, task_id=f"{pipeline_id}-dev"
                )
            elif task_type == "refactor":
                dev_result = await self.dev_agent.refactor(
                    task, working_dir, task_id=f"{pipeline_id}-dev"
                )
            else:
                dev_result = await self.dev_agent.custom_task(
                    task, working_dir, task_id=f"{pipeline_id}-dev"
                )

            result.dev_result = dev_result

            if not dev_result.success:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Dev Agent failed: {dev_result.error}"
                return result

            print(f"\nDev Agent Output:\n{dev_result.content[:500]}...")

        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.success = False
            result.error = f"Dev Agent error: {str(e)}"
            return result

        # ============================================================
        # Stage 4: Dev Approval
        # ============================================================
        result.stage = PipelineStage.DEV_APPROVAL

        if require_approvals:
            print("\n[STAGE 4/8] Dev Approval - Human Review Required")
            print("-" * 40)

            try:
                approval = await require_approval(
                    self.approval_gate,
                    agent="dev",
                    action="code_changes",
                    description=f"Dev Agent completed: {task}",
                    details={
                        "task_id": dev_result.task_id,
                        "files_changed": dev_result.files_changed or ["See output above"],
                        "summary": dev_result.content[:300] + "..." if len(dev_result.content) > 300 else dev_result.content
                    }
                )
                result.approvals.append(approval.to_dict())

            except PermissionError as e:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Dev approval rejected: {str(e)}"
                return result
        else:
            print("\n[STAGE 4/8] Dev Approval - Skipped (auto-approve mode)")

        # ============================================================
        # Stage 5: Test Agent
        # ============================================================
        result.stage = PipelineStage.TEST
        print("\n[STAGE 5/8] Test Agent - Generating Tests...")
        print("-" * 40)

        try:
            test_result = await self.test_agent.generate_tests(
                description=task,
                working_dir=working_dir,
                task_id=f"{pipeline_id}-test",
                dev_context=dev_result.content,
                files_changed=dev_result.files_changed
            )

            result.test_result = test_result

            if not test_result.success:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Test Agent failed: {test_result.error}"
                return result

            print(f"\nTest Agent Output:\n{test_result.content[:500]}...")

        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.success = False
            result.error = f"Test Agent error: {str(e)}"
            return result

        # ============================================================
        # Stage 4: Test Approval
        # ============================================================
        result.stage = PipelineStage.TEST_APPROVAL

        if require_approvals:
            print("\n[STAGE 6/8] Test Approval - Human Review Required")
            print("-" * 40)

            try:
                approval = await require_approval(
                    self.approval_gate,
                    agent="test",
                    action="test_generation",
                    description=f"Test Agent completed tests for: {task}",
                    details={
                        "task_id": test_result.task_id,
                        "files_changed": test_result.files_changed or ["See output above"],
                        "summary": test_result.content[:300] + "..." if len(test_result.content) > 300 else test_result.content
                    }
                )
                result.approvals.append(approval.to_dict())

            except PermissionError as e:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Test approval rejected: {str(e)}"
                return result
        else:
            print("\n[STAGE 6/8] Test Approval - Skipped (auto-approve mode)")

        # ============================================================
        # Stage 7: Cyber Agent - Security Scan
        # ============================================================
        result.stage = PipelineStage.CYBER
        print("\n[STAGE 7/8] Cyber Agent - Security Scan...")
        print("-" * 40)

        try:
            # Combine files from dev and test for scanning
            all_files = list(set(
                (dev_result.files_changed or []) +
                (test_result.files_changed or [])
            ))

            cyber_result = await self.cyber_agent.scan(
                description=f"Security scan for: {task}",
                working_dir=working_dir,
                task_id=f"{pipeline_id}-cyber",
                files_to_scan=all_files if all_files else None,
                context=f"Dev changes:\n{dev_result.content[:500]}\n\nTest changes:\n{test_result.content[:500]}"
            )

            result.cyber_result = cyber_result

            if not cyber_result.success:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Cyber Agent failed: {cyber_result.error}"
                return result

            # Parse the security decision
            decision, blockers = self.cyber_agent.parse_decision(cyber_result)
            result.security_decision = decision
            result.security_blockers = blockers

            print(f"\nCyber Agent Output:\n{cyber_result.content[:500]}...")
            print(f"\nSecurity Decision: {decision}")

        except Exception as e:
            result.stage = PipelineStage.FAILED
            result.success = False
            result.error = f"Cyber Agent error: {str(e)}"
            return result

        # ============================================================
        # Stage 6: Security Gate
        # ============================================================
        result.stage = PipelineStage.CYBER_APPROVAL

        if result.security_decision == "BLOCK":
            # Critical/High security issues - BLOCK the pipeline
            print("\n[STAGE 8/8] SECURITY GATE - BLOCKED")
            print("-" * 40)
            print("\n" + "!" * 60)
            print("PIPELINE BLOCKED - SECURITY ISSUES DETECTED")
            print("!" * 60)
            print("\nBlocking issues:")
            for blocker in result.security_blockers:
                print(f"  - {blocker}")
            print("\nThe pipeline cannot proceed until security issues are resolved.")
            print("Review the Cyber Agent output above for details.")

            result.stage = PipelineStage.BLOCKED
            result.success = False
            result.error = f"Security gate blocked: {', '.join(result.security_blockers)}"
            return result

        elif result.security_decision == "WARN":
            # Medium severity - require human approval
            print("\n[STAGE 8/8] Security Gate - WARNING (Human Review Required)")
            print("-" * 40)

            if require_approvals:
                try:
                    approval = await require_approval(
                        self.approval_gate,
                        agent="cyber",
                        action="security_warning",
                        description=f"Cyber Agent found warnings for: {task}",
                        details={
                            "task_id": cyber_result.task_id,
                            "decision": "WARN - Medium severity findings",
                            "summary": cyber_result.content[:500] + "..." if len(cyber_result.content) > 500 else cyber_result.content
                        }
                    )
                    result.approvals.append(approval.to_dict())
                    print("\nSecurity warnings acknowledged - proceeding.")

                except PermissionError as e:
                    result.stage = PipelineStage.BLOCKED
                    result.success = False
                    result.error = f"Security review rejected: {str(e)}"
                    return result
            else:
                print("\nSecurity warnings auto-acknowledged (auto-approve mode)")

        else:
            # APPROVE - clean scan
            print("\n[STAGE 8/8] Security Gate - APPROVED")
            print("-" * 40)
            print("\nNo critical security issues found.")

        # ============================================================
        # Complete
        # ============================================================
        result.stage = PipelineStage.COMPLETE
        result.success = True

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Pipeline ID: {pipeline_id}")
        print(f"Dev Task ID: {dev_result.task_id}")
        print(f"Test Task ID: {test_result.task_id}")
        print(f"Cyber Task ID: {cyber_result.task_id}")
        print(f"Security: {result.security_decision}")
        print(f"Approvals: {len(result.approvals)}")
        print("=" * 60 + "\n")

        return result


# Backwards compatibility alias
DevTestPipeline = DevTestCyberPipeline


class FullCICDPipeline(DevTestCyberPipeline):
    """
    Full pipeline: Design -> Dev -> Test -> Cyber -> Build -> Deploy

    Extends DevTestCyberPipeline with CI/CD stages for Jenkins builds,
    Artifactory artifact management, and environment deployments.
    """

    def __init__(
        self,
        store_path: str = "./context_store",
        jenkins_config: Optional[dict] = None,
        artifactory_config: Optional[dict] = None,
        deployment_config: Optional[dict] = None
    ):
        super().__init__(store_path)

        # Import here to avoid circular imports
        from .agents.cicd_agent import CICDAgent

        self.cicd_agent = CICDAgent(
            store_path=store_path,
            jenkins_config=jenkins_config,
            artifactory_config=artifactory_config
        )
        self.deployment_config = deployment_config or {}

    async def run(
        self,
        task: str,
        task_type: str = "feature",
        working_dir: str = ".",
        require_approvals: bool = True,
        skip_design: bool = False,
        deploy_to: Optional[list[str]] = None,
        jenkins_job: Optional[str] = None,
        artifact_path: Optional[str] = None
    ) -> PipelineResult:
        """
        Run the full Design -> Dev -> Test -> Cyber -> Build -> Deploy pipeline.

        Args:
            task: Task description
            task_type: Type of task (feature, bugfix, refactor)
            working_dir: Directory to work in
            require_approvals: Whether to require human approvals
            skip_design: Skip design phase
            deploy_to: List of environments to deploy to ["dev", "staging", "prod"]
            jenkins_job: Jenkins job name to trigger
            artifact_path: Path to artifact for upload (if not using Jenkins)

        Returns:
            PipelineResult with outcomes from all stages
        """
        # Run parent pipeline stages (Design -> Dev -> Test -> Cyber)
        result = await super().run(
            task=task,
            task_type=task_type,
            working_dir=working_dir,
            require_approvals=require_approvals,
            skip_design=skip_design
        )

        # If parent pipeline failed, return early
        if not result.success:
            return result

        # Continue with CI/CD stages if deploy_to is specified
        if deploy_to:
            result = await self._run_cicd_stages(
                result=result,
                working_dir=working_dir,
                deploy_to=deploy_to,
                require_approvals=require_approvals,
                jenkins_job=jenkins_job,
                artifact_path=artifact_path
            )

        return result

    async def _run_cicd_stages(
        self,
        result: PipelineResult,
        working_dir: str,
        deploy_to: list[str],
        require_approvals: bool,
        jenkins_job: Optional[str] = None,
        artifact_path: Optional[str] = None
    ) -> PipelineResult:
        """
        Run CI/CD stages after security approval.

        Args:
            result: Result from parent pipeline
            working_dir: Working directory
            deploy_to: Environments to deploy to
            require_approvals: Whether to require approvals
            jenkins_job: Jenkins job to trigger
            artifact_path: Artifact path for upload

        Returns:
            Updated PipelineResult
        """
        from .agents.cicd_agent import Environment
        from .approval import require_dual_approval

        pipeline_id = result.pipeline_id

        # ============================================================
        # Stage 9: Build (Jenkins)
        # ============================================================
        if jenkins_job:
            result.stage = PipelineStage.BUILD
            print("\n[STAGE 9] CI/CD Agent - Triggering Jenkins Build...")
            print("-" * 40)

            try:
                build_result = await self.cicd_agent.trigger_build(
                    job_name=jenkins_job,
                    parameters={"TASK": result.dev_result.task_id if result.dev_result else ""},
                    working_dir=working_dir,
                    task_id=f"{pipeline_id}-build",
                    pipeline_id=pipeline_id
                )

                result.cicd_result = build_result

                if not build_result.success:
                    result.stage = PipelineStage.FAILED
                    result.success = False
                    result.error = f"Build failed: {build_result.error}"
                    return result

                print(f"\n{build_result.content}")

                # Extract build number from result (simplified parsing)
                for line in build_result.content.split("\n"):
                    if "Build Number:" in line:
                        try:
                            result.build_number = int(line.split(":")[-1].strip())
                        except ValueError:
                            pass

            except Exception as e:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Build error: {str(e)}"
                return result

        # ============================================================
        # Stage 10: Artifact Upload (Artifactory)
        # ============================================================
        if artifact_path:
            result.stage = PipelineStage.ARTIFACT_UPLOAD
            print("\n[STAGE 10] CI/CD Agent - Uploading Artifact...")
            print("-" * 40)

            # Generate version from build number or timestamp
            import time
            version = f"1.0.{result.build_number}" if result.build_number else f"1.0.{int(time.time())}"

            try:
                upload_result = await self.cicd_agent.upload_artifact(
                    artifact_path=artifact_path,
                    version=version,
                    working_dir=working_dir,
                    task_id=f"{pipeline_id}-upload",
                    pipeline_id=pipeline_id
                )

                if not upload_result.success:
                    result.stage = PipelineStage.FAILED
                    result.success = False
                    result.error = f"Artifact upload failed: {upload_result.error}"
                    return result

                result.artifact_version = version
                print(f"\n{upload_result.content}")

                # Extract SHA-256 from result
                for line in upload_result.content.split("\n"):
                    if "SHA-256:" in line:
                        result.artifact_sha256 = line.split(":")[-1].strip()

            except Exception as e:
                result.stage = PipelineStage.FAILED
                result.success = False
                result.error = f"Artifact upload error: {str(e)}"
                return result

        # ============================================================
        # Deployment Stages
        # ============================================================
        for env_name in deploy_to:
            env = Environment(env_name.lower())

            if env == Environment.DEV:
                # Dev: auto-deploy
                result.stage = PipelineStage.DEPLOY_DEV
                print(f"\n[STAGE] CI/CD Agent - Deploying to {env_name}...")
                print("-" * 40)

                deploy_result = await self.cicd_agent.deploy(
                    environment=env,
                    artifact_version=result.artifact_version or "latest",
                    artifact_sha256=result.artifact_sha256 or "",
                    working_dir=working_dir,
                    task_id=f"{pipeline_id}-deploy-{env_name}",
                    pipeline_id=pipeline_id,
                    approved_by=[]  # No approval needed for dev
                )

                result.deployment_results[env_name] = deploy_result.success
                if not deploy_result.success:
                    print(f"\nWarning: {env_name} deployment failed: {deploy_result.error}")

            elif env == Environment.STAGING:
                # Staging: single approval
                result.stage = PipelineStage.DEPLOY_STAGING_APPROVAL

                if require_approvals:
                    print(f"\n[STAGE] Staging Deployment Approval Required")
                    print("-" * 40)

                    try:
                        approval = await require_approval(
                            self.approval_gate,
                            agent="cicd",
                            action="deployment_staging",
                            description=f"Deploy {result.artifact_version} to staging",
                            details={
                                "artifact_version": result.artifact_version,
                                "artifact_sha256": result.artifact_sha256,
                                "pipeline_id": pipeline_id
                            }
                        )
                        result.approvals.append(approval.to_dict())
                        approver = approval.approver or "user"

                    except PermissionError as e:
                        result.stage = PipelineStage.FAILED
                        result.success = False
                        result.error = f"Staging deployment rejected: {str(e)}"
                        return result
                else:
                    approver = "auto-approved"

                result.stage = PipelineStage.DEPLOY_STAGING
                print(f"\n[STAGE] CI/CD Agent - Deploying to staging...")
                print("-" * 40)

                deploy_result = await self.cicd_agent.deploy(
                    environment=env,
                    artifact_version=result.artifact_version or "latest",
                    artifact_sha256=result.artifact_sha256 or "",
                    working_dir=working_dir,
                    task_id=f"{pipeline_id}-deploy-staging",
                    pipeline_id=pipeline_id,
                    approved_by=[approver]
                )

                result.deployment_results["staging"] = deploy_result.success

            elif env == Environment.PROD:
                # Production: dual approval
                result.stage = PipelineStage.DEPLOY_PROD_APPROVAL

                if require_approvals:
                    print(f"\n[STAGE] Production Deployment - DUAL APPROVAL Required")
                    print("-" * 40)

                    try:
                        approval1, approval2 = await require_dual_approval(
                            self.approval_gate,
                            agent="cicd",
                            action="deployment_prod",
                            description=f"Deploy {result.artifact_version} to PRODUCTION",
                            details={
                                "artifact_version": result.artifact_version,
                                "artifact_sha256": result.artifact_sha256,
                                "pipeline_id": pipeline_id,
                                "environment": "PRODUCTION"
                            }
                        )
                        result.approvals.append(approval1.to_dict())
                        result.approvals.append(approval2.to_dict())
                        approvers = [approval1.approver or "user1", approval2.approver or "user2"]

                    except PermissionError as e:
                        result.stage = PipelineStage.FAILED
                        result.success = False
                        result.error = f"Production deployment rejected: {str(e)}"
                        return result
                else:
                    approvers = ["auto-approved-1", "auto-approved-2"]

                result.stage = PipelineStage.DEPLOY_PROD
                print(f"\n[STAGE] CI/CD Agent - Deploying to PRODUCTION...")
                print("-" * 40)

                deploy_result = await self.cicd_agent.deploy(
                    environment=env,
                    artifact_version=result.artifact_version or "latest",
                    artifact_sha256=result.artifact_sha256 or "",
                    working_dir=working_dir,
                    task_id=f"{pipeline_id}-deploy-prod",
                    pipeline_id=pipeline_id,
                    approved_by=approvers
                )

                result.deployment_results["prod"] = deploy_result.success

        # ============================================================
        # Complete
        # ============================================================
        result.stage = PipelineStage.COMPLETE
        result.success = True

        print("\n" + "=" * 60)
        print("FULL CI/CD PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Pipeline ID: {pipeline_id}")
        if result.build_number:
            print(f"Build Number: {result.build_number}")
        if result.artifact_version:
            print(f"Artifact Version: {result.artifact_version}")
        if result.deployment_results:
            print(f"Deployments: {result.deployment_results}")
        print(f"Approvals: {len(result.approvals)}")
        print("=" * 60 + "\n")

        return result
