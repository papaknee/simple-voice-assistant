"""Tests for protocol compatibility of fake adapter implementations."""

from __future__ import annotations

from assistant_core.fakes import (
    FakeAudioInput,
    FakeAudioOutput,
    FakeIntentRouter,
    FakeSkill,
    FakeSoundManager,
    FakeSpeechToTextEngine,
    FakeTextToSpeechEngine,
    FakeVoiceActivityDetector,
    FakeWakeWordDetector,
    InMemoryRuntimeEventBus,
)
from assistant_core.interfaces import (
    AudioInput,
    AudioOutput,
    IntentRouter,
    RuntimeEventBus,
    Skill,
    SoundManager,
    SpeechToTextEngine,
    TextToSpeechEngine,
    VoiceActivityDetector,
    WakeWordDetector,
)


def test_replaceable_component_protocols_are_runtime_checkable() -> None:
    assert isinstance(FakeAudioInput(), AudioInput)
    assert isinstance(FakeAudioOutput(), AudioOutput)
    assert isinstance(FakeWakeWordDetector(), WakeWordDetector)
    assert isinstance(FakeVoiceActivityDetector(), VoiceActivityDetector)
    assert isinstance(FakeSpeechToTextEngine(), SpeechToTextEngine)
    assert isinstance(FakeIntentRouter(), IntentRouter)
    assert isinstance(FakeSkill(), Skill)
    assert isinstance(FakeTextToSpeechEngine(), TextToSpeechEngine)
    assert isinstance(FakeSoundManager(), SoundManager)
    assert isinstance(InMemoryRuntimeEventBus(), RuntimeEventBus)
