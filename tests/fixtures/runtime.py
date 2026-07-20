"""Reusable runtime harness for tests based on fake adapters."""

from __future__ import annotations

from dataclasses import dataclass

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
)
from assistant_core.models import AssistantContext, IntentResolution
from assistant_core.runtime.event_bus import InMemoryRuntimeEventBus
from assistant_core.runtime.state_machine import AssistantRuntime
from assistant_core.skills import SkillExecutor


@dataclass(slots=True)
class RuntimeHarness:
    """Container for runtime and all fake components used in tests."""

    runtime: AssistantRuntime
    audio_input: FakeAudioInput
    audio_output: FakeAudioOutput
    wake: FakeWakeWordDetector
    vad: FakeVoiceActivityDetector
    stt: FakeSpeechToTextEngine
    router: FakeIntentRouter
    skill: FakeSkill
    tts: FakeTextToSpeechEngine
    sounds: FakeSoundManager
    bus: InMemoryRuntimeEventBus


def build_runtime_harness(
    *,
    context: AssistantContext | None = None,
    stt: FakeSpeechToTextEngine | None = None,
    router: FakeIntentRouter | None = None,
    skill: FakeSkill | None = None,
    skill_executor: SkillExecutor | None = None,
) -> RuntimeHarness:
    """Build a deterministic assistant runtime wired to reusable fake components."""

    audio_input = FakeAudioInput()
    audio_output = FakeAudioOutput()
    wake = FakeWakeWordDetector(wake_frame=b"wake")
    vad = FakeVoiceActivityDetector(stop_after_silence_frames=2)
    stt_engine = stt or FakeSpeechToTextEngine(transcript_text="hello")
    intent_router = router or FakeIntentRouter(
        routes={"hello": IntentResolution(intent_name="echo_debug", confidence=1.0)}
    )
    selected_skill = skill or FakeSkill(skill_name="echo_debug")
    tts = FakeTextToSpeechEngine()
    sounds = FakeSoundManager()
    bus = InMemoryRuntimeEventBus()
    runtime = AssistantRuntime(
        audio_input=audio_input,
        audio_output=audio_output,
        wake_detector=wake,
        vad=vad,
        stt=stt_engine,
        intent_router=intent_router,
        skills=[selected_skill],
        tts=tts,
        sound_manager=sounds,
        event_bus=bus,
        context=context or AssistantContext(session_id="session-1", turn_id="turn-1"),
        skill_executor=skill_executor or SkillExecutor(),
    )
    return RuntimeHarness(
        runtime=runtime,
        audio_input=audio_input,
        audio_output=audio_output,
        wake=wake,
        vad=vad,
        stt=stt_engine,
        router=intent_router,
        skill=selected_skill,
        tts=tts,
        sounds=sounds,
        bus=bus,
    )
