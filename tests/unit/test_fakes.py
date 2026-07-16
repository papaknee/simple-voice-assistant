"""Tests for fake adapters used by runtime and fixture-based testing."""

from __future__ import annotations

import pytest
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
from assistant_core.interfaces import SynthesizedAudio
from assistant_core.models import (
    AssistantContext,
    CapturedAudio,
    IntentResolution,
    SkillRequest,
)


def test_fake_audio_input_requires_start_before_read() -> None:
    adapter = FakeAudioInput(frames=[b"abc"])
    with pytest.raises(RuntimeError, match="must be started"):
        adapter.read_frames()

    adapter.start()
    assert adapter.read_frames() == b"abc"
    assert adapter.read_frames() == b""


def test_fake_audio_output_rejects_play_after_stop() -> None:
    adapter = FakeAudioOutput()
    adapter.stop()
    with pytest.raises(RuntimeError, match="stopped"):
        adapter.play(SynthesizedAudio(b"\x00", 22050, 1, 2))


def test_fake_wake_detector_requires_load_and_detects_wake_frame() -> None:
    detector = FakeWakeWordDetector(wake_frame=b"wake")
    with pytest.raises(RuntimeError, match="must be loaded"):
        detector.process_frame(b"wake")

    detector.load()
    assert detector.process_frame(b"wake").detected is True
    assert detector.process_frame(b"other").detected is False


def test_fake_vad_stops_after_speech_then_silence_threshold() -> None:
    vad = FakeVoiceActivityDetector(stop_after_silence_frames=2)
    vad.process_frame(b"speech")
    assert vad.is_speech() is True
    assert vad.should_stop_recording() is False

    vad.process_frame(b"")
    assert vad.should_stop_recording() is False
    vad.process_frame(b"")
    assert vad.should_stop_recording() is True


def test_fake_stt_tts_skill_and_router_pipeline_shapes() -> None:
    context = AssistantContext(session_id="session-1")
    audio = CapturedAudio(
        sample_rate_hz=16000,
        channels=1,
        sample_width_bytes=2,
        frame_count=16000,
        duration_seconds=1.0,
    )
    stt = FakeSpeechToTextEngine(transcript_text="hello")
    transcript = stt.transcribe(b"\x00", audio)
    assert transcript.text == "hello"

    router = FakeIntentRouter(
        routes={"hello": IntentResolution(intent_name="echo_debug", confidence=1.0)}
    )
    intent = router.route(transcript, context)
    assert intent.intent_name == "echo_debug"

    skill = FakeSkill()
    request = SkillRequest(
        skill_name="echo_debug", transcript=transcript, intent=intent, context=context
    )
    result = skill.run(request, context)
    assert result.success is True
    assert result.spoken_response is not None

    tts = FakeTextToSpeechEngine()
    synthesized = tts.synthesize(result.spoken_response or "")
    assert synthesized.audio_bytes


def test_fake_sound_manager_validates_required_cues() -> None:
    valid = FakeSoundManager()
    assert valid.validate_pack() == []

    invalid = FakeSoundManager(available_cues=("wake_detected",))
    errors = invalid.validate_pack()
    assert errors and errors[0].code == "missing_sound_cues"
    with pytest.raises(ValueError, match="Unknown sound cue"):
        invalid.play("error")
