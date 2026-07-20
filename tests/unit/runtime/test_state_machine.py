"""Tests for skeleton assistant runtime state-machine behavior."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from assistant_core.fakes import FakeIntentRouter, FakeSpeechToTextEngine
from assistant_core.interfaces import SkillMetadata
from assistant_core.models import AssistantContext, IntentResolution, SkillRequest, SkillResult
from assistant_core.runtime.events import RuntimeEventType, RuntimeState
from assistant_core.skills import TimeDateSkill
from tests.fixtures.runtime import RuntimeHarness


def test_runtime_start_and_shutdown_publish_lifecycle_events(
    runtime_harness: RuntimeHarness,
) -> None:
    runtime_harness.runtime.start()
    runtime_harness.runtime.shutdown()

    event_types = [event.event_type for event in runtime_harness.bus.history()]
    assert RuntimeEventType.STATE_TRANSITIONED in event_types
    assert RuntimeEventType.SHUTDOWN_COMPLETED in event_types
    assert runtime_harness.runtime.state == RuntimeState.SHUTDOWN


def test_runtime_processes_fake_pipeline_and_returns_to_idle(
    runtime_harness: RuntimeHarness,
) -> None:
    runtime_harness.runtime.start()
    runtime_harness.runtime.process_audio_frame(b"wake")
    runtime_harness.runtime.process_audio_frame(b"speech")
    runtime_harness.runtime.process_audio_frame(b"")
    runtime_harness.runtime.process_audio_frame(b"")

    event_types = [event.event_type for event in runtime_harness.bus.history()]
    assert RuntimeEventType.WAKE_DETECTED in event_types
    assert RuntimeEventType.TRANSCRIPTION_COMPLETED in event_types
    assert RuntimeEventType.INTENT_ROUTED in event_types
    assert RuntimeEventType.SKILL_EXECUTED in event_types
    assert RuntimeEventType.RESPONSE_RENDERED in event_types
    assert runtime_harness.audio_output.played
    assert "wake_detected" in runtime_harness.sounds.played_cues
    assert "success" in runtime_harness.sounds.played_cues
    assert runtime_harness.runtime.state == RuntimeState.IDLE_LISTENING


def test_runtime_recovers_to_idle_when_transcription_raises(
    runtime_harness_factory: Callable[..., RuntimeHarness],
) -> None:
    harness = runtime_harness_factory(
        stt=FakeSpeechToTextEngine(transcript_text="bad", confidence=1.5),
        router=FakeIntentRouter(),
    )
    harness.runtime.start()
    harness.runtime.process_audio_frame(b"wake")
    harness.runtime.process_audio_frame(b"speech")
    harness.runtime.process_audio_frame(b"")
    harness.runtime.process_audio_frame(b"")

    event_types = [event.event_type for event in harness.bus.history()]
    assert RuntimeEventType.ERROR_RAISED in event_types
    assert RuntimeEventType.RECOVERY_COMPLETED in event_types
    assert "error" in harness.sounds.played_cues
    assert harness.runtime.state == RuntimeState.IDLE_LISTENING


@dataclass(slots=True)
class ShellSkill:
    """Skill that requires a dangerous permission for runtime integration tests."""

    skill_name: str = "echo_debug"

    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name=self.skill_name, description="Shell-backed skill")

    def can_handle(self, intent: IntentResolution) -> bool:
        return intent.intent_name == self.skill_name

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult:
        _ = (request, context)
        return SkillResult(skill_name=self.skill_name, success=True, spoken_response="ok")

    def permissions(self) -> set[str]:
        return {"shell"}


def test_runtime_marks_skill_permission_denials_as_error_results(
    runtime_harness_factory: Callable[..., RuntimeHarness],
) -> None:
    harness = runtime_harness_factory(skill=ShellSkill())

    harness.runtime.start()
    harness.runtime.process_audio_frame(b"wake")
    harness.runtime.process_audio_frame(b"speech")
    harness.runtime.process_audio_frame(b"")
    harness.runtime.process_audio_frame(b"")

    skill_events = [
        event for event in harness.bus.history() if event.event_type == RuntimeEventType.SKILL_EXECUTED
    ]

    assert skill_events
    assert skill_events[-1].payload == {"skill_name": "echo_debug", "success": False}
    assert "error" in harness.sounds.played_cues
    assert harness.runtime.state == RuntimeState.IDLE_LISTENING


def test_runtime_can_select_shared_time_date_skill_by_can_handle(
    runtime_harness_factory: Callable[..., RuntimeHarness],
) -> None:
    harness = runtime_harness_factory(
        router=FakeIntentRouter(
            routes={"hello": IntentResolution(intent_name="get_time", confidence=1.0)}
        ),
        skill=TimeDateSkill(),
    )

    harness.runtime.start()
    harness.runtime.process_audio_frame(b"wake")
    harness.runtime.process_audio_frame(b"speech")
    harness.runtime.process_audio_frame(b"")
    harness.runtime.process_audio_frame(b"")

    skill_events = [
        event for event in harness.bus.history() if event.event_type == RuntimeEventType.SKILL_EXECUTED
    ]
    assert skill_events
    assert skill_events[-1].payload == {"skill_name": "time_date", "success": True}
    assert harness.audio_output.played
