"""Human-in-the-loop approval mechanism."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"


@dataclass
class ApprovalRequest:
    """A request for human approval."""
    request_id: str
    agent: str
    action: str
    description: str
    details: dict
    timestamp: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver: Optional[str] = None
    approval_timestamp: Optional[str] = None
    comments: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalRequest":
        data["status"] = ApprovalStatus(data["status"])
        return cls(**data)


class ApprovalGate:
    """
    Human-in-the-loop approval gate.

    Used to pause agent workflows and request human approval
    before proceeding with sensitive operations.
    """

    def __init__(self, store_path: str = "./context_store"):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.approvals_file = self.store_path / "approvals.json"

    def request_approval(
        self,
        agent: str,
        action: str,
        description: str,
        details: Optional[dict] = None
    ) -> ApprovalRequest:
        """
        Create an approval request.

        Args:
            agent: Name of the agent requesting approval
            action: Type of action requiring approval
            description: Human-readable description
            details: Additional details about the request

        Returns:
            ApprovalRequest object
        """
        import uuid

        request = ApprovalRequest(
            request_id=f"approval-{uuid.uuid4().hex[:8]}",
            agent=agent,
            action=action,
            description=description,
            details=details or {},
            timestamp=datetime.now().isoformat(),
        )

        self._save_request(request)
        return request

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        approvals = self._load_approvals()
        return [
            ApprovalRequest.from_dict(a)
            for a in approvals.values()
            if a["status"] == ApprovalStatus.PENDING.value
        ]

    def approve(
        self,
        request_id: str,
        approver: str = "user",
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Approve a request.

        Args:
            request_id: ID of the request to approve
            approver: Name of the approver
            comments: Optional approval comments

        Returns:
            Updated ApprovalRequest
        """
        return self._update_status(
            request_id,
            ApprovalStatus.APPROVED,
            approver,
            comments
        )

    def reject(
        self,
        request_id: str,
        approver: str = "user",
        comments: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Reject a request.

        Args:
            request_id: ID of the request to reject
            approver: Name of the approver
            comments: Reason for rejection

        Returns:
            Updated ApprovalRequest
        """
        return self._update_status(
            request_id,
            ApprovalStatus.REJECTED,
            approver,
            comments
        )

    def check_status(self, request_id: str) -> Optional[ApprovalRequest]:
        """Check the status of an approval request."""
        approvals = self._load_approvals()
        if request_id in approvals:
            return ApprovalRequest.from_dict(approvals[request_id])
        return None

    def _update_status(
        self,
        request_id: str,
        status: ApprovalStatus,
        approver: str,
        comments: Optional[str]
    ) -> ApprovalRequest:
        """Update the status of a request."""
        approvals = self._load_approvals()

        if request_id not in approvals:
            raise ValueError(f"Approval request not found: {request_id}")

        approvals[request_id]["status"] = status.value
        approvals[request_id]["approver"] = approver
        approvals[request_id]["approval_timestamp"] = datetime.now().isoformat()
        approvals[request_id]["comments"] = comments

        self._save_approvals(approvals)
        return ApprovalRequest.from_dict(approvals[request_id])

    def _save_request(self, request: ApprovalRequest) -> None:
        """Save a new approval request."""
        approvals = self._load_approvals()
        approvals[request.request_id] = request.to_dict()
        self._save_approvals(approvals)

    def _load_approvals(self) -> dict:
        """Load all approvals."""
        if self.approvals_file.exists():
            return json.loads(self.approvals_file.read_text())
        return {}

    def _save_approvals(self, approvals: dict) -> None:
        """Save all approvals."""
        self.approvals_file.write_text(json.dumps(approvals, indent=2))


def prompt_for_approval(request: ApprovalRequest) -> tuple[bool, str]:
    """
    Prompt the user for approval in the CLI.

    Args:
        request: The approval request

    Returns:
        Tuple of (approved: bool, comments: str)
    """
    print("\n" + "=" * 60)
    print("APPROVAL REQUIRED")
    print("=" * 60)
    print(f"\nAgent: {request.agent}")
    print(f"Action: {request.action}")
    print(f"Description: {request.description}")

    if request.details:
        print("\nDetails:")
        for key, value in request.details.items():
            if isinstance(value, list):
                print(f"  {key}:")
                for item in value:
                    print(f"    - {item}")
            else:
                print(f"  {key}: {value}")

    print("\n" + "-" * 60)

    while True:
        response = input("\nApprove? [y/n/details]: ").strip().lower()

        if response in ("y", "yes"):
            comments = input("Comments (optional): ").strip()
            return True, comments

        elif response in ("n", "no"):
            comments = input("Reason for rejection: ").strip()
            return False, comments

        elif response in ("d", "details"):
            print("\nFull details:")
            print(json.dumps(request.details, indent=2))

        else:
            print("Please enter 'y' to approve, 'n' to reject, or 'd' for details")


async def require_approval(
    gate: ApprovalGate,
    agent: str,
    action: str,
    description: str,
    details: Optional[dict] = None,
    auto_prompt: bool = True
) -> ApprovalRequest:
    """
    Require human approval before proceeding.

    Args:
        gate: ApprovalGate instance
        agent: Name of the agent
        action: Type of action
        description: Human-readable description
        details: Additional details
        auto_prompt: Whether to automatically prompt for approval

    Returns:
        ApprovalRequest with final status

    Raises:
        PermissionError: If approval is rejected
    """
    request = gate.request_approval(agent, action, description, details)

    if auto_prompt:
        approved, comments = prompt_for_approval(request)

        if approved:
            request = gate.approve(request.request_id, "user", comments)
            print("\n Approved\n")
        else:
            request = gate.reject(request.request_id, "user", comments)
            print("\n Rejected\n")
            raise PermissionError(f"Approval rejected: {comments}")

    return request


async def require_dual_approval(
    gate: ApprovalGate,
    agent: str,
    action: str,
    description: str,
    details: Optional[dict] = None,
    authorized_approvers: Optional[list[str]] = None
) -> tuple[ApprovalRequest, ApprovalRequest]:
    """
    Require two different approvers for sensitive operations.

    This enforces separation of duties for regulated environments,
    particularly production deployments.

    Args:
        gate: ApprovalGate instance
        agent: Name of the agent requesting approval
        action: Type of action requiring approval
        description: Human-readable description
        details: Additional details about the request
        authorized_approvers: Optional list of authorized approvers

    Returns:
        Tuple of (first_approval, second_approval)

    Raises:
        PermissionError: If either approval is rejected
    """
    print("\n" + "=" * 60)
    print("DUAL APPROVAL REQUIRED")
    print("=" * 60)
    print("This action requires approval from TWO different approvers.")
    print("=" * 60 + "\n")

    # First approval
    print("[Approval 1 of 2]")
    request1 = gate.request_approval(
        agent,
        action,
        f"[Primary] {description}",
        details
    )
    approved1, comments1 = prompt_for_approval(request1)

    if not approved1:
        request1 = gate.reject(request1.request_id, "user", comments1)
        raise PermissionError(f"First approval rejected: {comments1}")

    request1 = gate.approve(request1.request_id, "user", comments1)
    first_approver = request1.approver
    print(f"\n First approval granted by: {first_approver}\n")

    # Second approval (must be different person)
    print("[Approval 2 of 2]")
    print(f"Note: Must be different from first approver ({first_approver})")

    details_with_context = details.copy() if details else {}
    details_with_context["first_approver"] = first_approver
    details_with_context["requires_different_approver"] = True

    while True:
        request2 = gate.request_approval(
            agent,
            f"{action}_secondary",
            f"[Secondary] {description}",
            details_with_context
        )
        approved2, comments2 = prompt_for_approval(request2)

        if not approved2:
            request2 = gate.reject(request2.request_id, "user", comments2)
            raise PermissionError(f"Second approval rejected: {comments2}")

        # For CLI, we need to ask who the second approver is
        second_approver = input("Enter your username/email: ").strip()

        if second_approver == first_approver:
            print(f"\n Error: Second approver must be different from {first_approver}")
            print("Please have a different person approve.\n")
            continue

        # Check against authorized approvers if provided
        if authorized_approvers and second_approver not in authorized_approvers:
            print(f"\n Error: {second_approver} is not an authorized approver")
            print(f"Authorized approvers: {', '.join(authorized_approvers)}\n")
            continue

        request2 = gate.approve(request2.request_id, second_approver, comments2)
        break

    print(f"\n Second approval granted by: {second_approver}")
    print("\n Dual approval complete\n")

    return request1, request2


# Common approval action types for CI/CD
class ApprovalAction:
    """Standard approval action types."""
    CODE_REVIEW = "code_review"
    TEST_REVIEW = "test_review"
    SECURITY_REVIEW = "security_review"
    DESIGN_REVIEW = "design_review"
    DEPLOYMENT_DEV = "deployment_dev"
    DEPLOYMENT_STAGING = "deployment_staging"
    DEPLOYMENT_PROD = "deployment_prod"
    ROLLBACK = "rollback"
