"""Permission-aware skill execution helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from time import monotonic

from assistant_core.interfaces import Skill
from assistant_core.models import AssistantContext, AssistantError, SkillRequest, SkillResult

SKILL_PERMISSIONS = frozenset(
    {
        "network",
        "filesystem_read",
        "filesystem_write",
        "gpio",
        "shell",
        "home_automation",
    }
)

DANGEROUS_SKILL_PERMISSIONS = frozenset(
    {
        "network",
        "filesystem_write",
        "gpio",
        "shell",
        "home_automation",
    }
)


@dataclass(frozen=True, slots=True)
class SkillExecutionPolicy:
    """Permission and timeout policy applied before skill execution."""

    allowed_permissions: frozenset[str] = frozenset({"filesystem_read"})
    default_timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        unknown_permissions = self.allowed_permissions.difference(SKILL_PERMISSIONS)
        if unknown_permissions:
            unknown_values = ", ".join(sorted(unknown_permissions))
            raise ValueError(f"Unknown skill permissions in policy: {unknown_values}")
        if self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be > 0.")


@dataclass(slots=True)
class SkillExecutor:
    """Execute skills with permission checks and timeout/cancellation guards."""

    policy: SkillExecutionPolicy = SkillExecutionPolicy()

    def execute(
        self,
        skill: Skill,
        request: SkillRequest,
        context: AssistantContext,
        *,
        timeout_seconds: float | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> SkillResult:
        """Run a skill and return a structured result for success or failure."""
        effective_timeout = self.policy.default_timeout_seconds if timeout_seconds is None else timeout_seconds
        if effective_timeout <= 0:
            raise ValueError("timeout_seconds must be > 0.")

        requested_permissions = frozenset(skill.permissions())
        unknown_permissions = requested_permissions.difference(SKILL_PERMISSIONS)
        if unknown_permissions:
            return self._error_result(
                request.skill_name,
                code="skill_execution.unknown_permission",
                message="Skill requested unknown permissions.",
                details={
                    "unknown_permissions": sorted(unknown_permissions),
                    "requested_permissions": sorted(requested_permissions),
                },
            )

        denied_permissions = requested_permissions.difference(self.policy.allowed_permissions)
        if denied_permissions:
            return self._error_result(
                request.skill_name,
                code="skill_execution.permission_denied",
                message="Skill requested permissions that are not allowed.",
                details={
                    "allowed_permissions": sorted(self.policy.allowed_permissions),
                    "dangerous_permissions": sorted(requested_permissions.intersection(DANGEROUS_SKILL_PERMISSIONS)),
                    "denied_permissions": sorted(denied_permissions),
                    "requested_permissions": sorted(requested_permissions),
                },
            )

        if cancel_requested is not None and cancel_requested():
            return self._error_result(
                request.skill_name,
                code="skill_execution.cancelled",
                message="Skill execution was cancelled before it started.",
            )

        result_queue: Queue[SkillResult | BaseException | object] = Queue(maxsize=1)

        def _run_skill() -> None:
            try:
                result_queue.put(skill.run(request, context))
            except BaseException as exc:  # pragma: no cover - exercised via tests
                result_queue.put(exc)

        execution_thread = Thread(
            target=_run_skill,
            name=f"skill-{request.skill_name}",
            daemon=True,
        )
        started = monotonic()
        execution_thread.start()

        while True:
            if cancel_requested is not None and cancel_requested():
                return self._error_result(
                    request.skill_name,
                    code="skill_execution.cancelled",
                    message="Skill execution was cancelled.",
                )

            remaining = effective_timeout - (monotonic() - started)
            if remaining <= 0:
                return self._error_result(
                    request.skill_name,
                    code="skill_execution.timeout",
                    message="Skill execution exceeded the configured timeout.",
                    details={"timeout_seconds": effective_timeout},
                )

            try:
                outcome = result_queue.get(timeout=min(0.01, remaining))
            except Empty:
                continue

            if isinstance(outcome, SkillResult):
                return outcome
            if isinstance(outcome, BaseException):
                return self._error_result(
                    request.skill_name,
                    code="skill_execution.failed",
                    message=str(outcome) or "Skill execution failed.",
                    details={"exception_type": type(outcome).__name__},
                )
            return self._error_result(
                request.skill_name,
                code="skill_execution.invalid_result",
                message="Skill returned an invalid result object.",
                details={"result_type": type(outcome).__name__},
            )

    def _error_result(
        self,
        skill_name: str,
        *,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> SkillResult:
        return SkillResult(
            skill_name=skill_name,
            success=False,
            error=AssistantError(
                code=code,
                message=message,
                recoverable=True,
                details=details or {},
            ),
        )