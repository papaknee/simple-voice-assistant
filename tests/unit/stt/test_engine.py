"""Unit tests for the STT adapter shell and fake engine."""

from __future__ import annotations

import pytest

from assistant_core.config.schema import SpeechToTextConfig
from assistant_core.interfaces import SpeechToTextEngine
from assistant_core.stt import FakeSpeechToTextEngine, create_stt_engine
from assistant_core.models import CapturedAudio, Transcript


def test_fake_stt_is_protocol_compatible_and_preserves_audio_metadata() -> None:
    engine = FakeSpeechToTextEngine(
        transcript_text="hello world",
        confidence=0.87,
        language_default="en-GB",
        backend_name="fake-stt",
        warnings=("low_confidence",),
    )
    audio = CapturedAudio(
        sample_rate_hz=16000,
        channels=1,
        sample_width_bytes=2,
        frame_count=8000,
        duration_seconds=0.5,
        source="microphone-1",
    )

    assert isinstance(engine, SpeechToTextEngine)

    transcript = engine.transcribe(b"\x00\x01", audio)

    assert isinstance(transcript, Transcript)
    assert transcript.text == "hello world"
    assert transcript.language == "en-GB"
    assert transcript.confidence == pytest.approx(0.87)
    assert transcript.duration_seconds == pytest.approx(0.5)
    assert transcript.metadata["backend_name"] == "fake-stt"
    assert transcript.metadata["warnings"] == ["low_confidence"]
    assert transcript.metadata["audio_frame_count"] == 8000
    assert transcript.metadata["audio_source"] == "microphone-1"


def test_fake_stt_uses_override_language_when_provided() -> None:
    engine = FakeSpeechToTextEngine(language_default="en-US")
    audio = CapturedAudio(
        sample_rate_hz=16000,
        channels=1,
        sample_width_bytes=2,
        frame_count=16000,
        duration_seconds=1.0,
    )

    transcript = engine.transcribe(b"\x00", audio, language="fr-FR")

    assert transcript.language == "fr-FR"


def test_create_stt_engine_returns_fake_engine_for_fake_config() -> None:
    config = SpeechToTextConfig(engine="fake", language="de-DE")

    engine = create_stt_engine(config)

    assert isinstance(engine, FakeSpeechToTextEngine)
    assert engine.language_default == "de-DE"


def test_create_stt_engine_rejects_unsupported_engine() -> None:
    config = SpeechToTextConfig(engine="whisper")

    with pytest.raises(RuntimeError, match="whisper"):
        create_stt_engine(config)