"""Unit tests for permission-aware skill execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event

import pytest

from assistant_core.interfaces import Skill, SkillMetadata
from assistant_core.models import AssistantContext, IntentResolution, SkillRequest, SkillResult, Transcript
from assistant_core.skills import SkillExecutionPolicy, SkillExecutor


@dataclass(slots=True)
class ControlledSkill(Skill):
    """Test double with configurable permissions and blocking behavior."""

    skill_name: str = "controlled"
    requested_permissions: set[str] = field(default_factory=set)
    block_event: Event | None = None
    raise_error: BaseException | None = None
    return_invalid_result: bool = False
    run_calls: int = 0

    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name=self.skill_name, description="Controlled test skill")

    def can_handle(self, intent: IntentResolution) -> bool:
        return intent.intent_name == self.skill_name

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult:
        _ = (request, context)
        self.run_calls += 1
        if self.block_event is not None:
            self.block_event.wait()
        if self.raise_error is not None:
            raise self.raise_error
        if self.return_invalid_result:
            return "invalid"  # type: ignore[return-value]
        return SkillResult(skill_name=self.skill_name, success=True, spoken_response="ok")

    def permissions(self) -> set[str]:
        return set(self.requested_permissions)


@pytest.fixture
def skill_request() -> SkillRequest:
    context = AssistantContext(session_id="session-1", turn_id="turn-1")
    transcript = Transcript(text="run controlled skill", confidence=1.0)
    intent = IntentResolution(intent_name="controlled", confidence=1.0)
    return SkillRequest(skill_name="controlled", transcript=transcript, intent=intent, context=context)


def test_executor_denies_unapproved_permissions(skill_request: SkillRequest) -> None:
    executor = SkillExecutor()
    skill = ControlledSkill(requested_permissions={"shell"})

    result = executor.execute(skill, skill_request, skill_request.context)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "skill_execution.permission_denied"
    assert result.error.details["denied_permissions"] == ["shell"]
    assert skill.run_calls == 0


def test_executor_allows_explicitly_enabled_dangerous_permissions(skill_request: SkillRequest) -> None:
    executor = SkillExecutor(
        SkillExecutionPolicy(allowed_permissions=frozenset({"filesystem_read", "shell"}))
    )
    skill = ControlledSkill(requested_permissions={"shell"})

    result = executor.execute(skill, skill_request, skill_request.context)

    assert result.success is True
    assert result.spoken_response == "ok"
    assert skill.run_calls == 1


def test_executor_times_out_long_running_skill(skill_request: SkillRequest) -> None:
    block_event = Event()
    executor = SkillExecutor(SkillExecutionPolicy(default_timeout_seconds=0.01))
    skill = ControlledSkill(requested_permissions={"filesystem_read"}, block_event=block_event)

    try:
        result = executor.execute(skill, skill_request, skill_request.context)
    finally:
        block_event.set()

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "skill_execution.timeout"


def test_executor_supports_pre_execution_cancellation(skill_request: SkillRequest) -> None:
    executor = SkillExecutor()
    skill = ControlledSkill(requested_permissions={"filesystem_read"})

    result = executor.execute(
        skill,
        skill_request,
        skill_request.context,
        cancel_requested=lambda: True,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "skill_execution.cancelled"
    assert skill.run_calls == 0


def test_executor_wraps_skill_exceptions(skill_request: SkillRequest) -> None:
    executor = SkillExecutor()
    skill = ControlledSkill(
        requested_permissions={"filesystem_read"},
        raise_error=RuntimeError("boom"),
    )

    result = executor.execute(skill, skill_request, skill_request.context)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "skill_execution.failed"
    assert result.error.details["exception_type"] == "RuntimeError"


def test_executor_rejects_invalid_result_values(skill_request: SkillRequest) -> None:
    executor = SkillExecutor()
    skill = ControlledSkill(requested_permissions={"filesystem_read"}, return_invalid_result=True)

    result = executor.execute(skill, skill_request, skill_request.context)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "skill_execution.invalid_result"