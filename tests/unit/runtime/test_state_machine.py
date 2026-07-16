"""Tests for skeleton assistant runtime state-machine behavior."""

from __future__ import annotations

from collections.abc import Callable

from assistant_core.fakes import FakeIntentRouter, FakeSpeechToTextEngine
from assistant_core.runtime.events import RuntimeEventType, RuntimeState
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
