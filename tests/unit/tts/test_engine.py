"""Unit tests for the TTS adapter shell and fake engine."""

from __future__ import annotations

import pytest

from assistant_core.config.schema import TextToSpeechConfig
from assistant_core.interfaces import SynthesizedAudio, TextToSpeechEngine
from assistant_core.tts import FakeTextToSpeechEngine, create_tts_engine


def test_fake_tts_is_protocol_compatible() -> None:
    engine = FakeTextToSpeechEngine()

    assert isinstance(engine, TextToSpeechEngine)


def test_fake_tts_synthesize_returns_synthesized_audio() -> None:
    engine = FakeTextToSpeechEngine(
        sample_rate_hz=22050,
        channels=1,
        sample_width_bytes=2,
    )

    result = engine.synthesize("hello world")

    assert isinstance(result, SynthesizedAudio)
    assert result.audio_bytes == b"hello world"
    assert result.sample_rate_hz == 22050
    assert result.channels == 1
    assert result.sample_width_bytes == 2
    assert result.format == "pcm_s16le"


def test_fake_tts_synthesize_empty_text_returns_empty_bytes() -> None:
    engine = FakeTextToSpeechEngine()

    result = engine.synthesize("")

    assert result.audio_bytes == b""


def test_fake_tts_synthesize_ignores_voice_and_options() -> None:
    engine = FakeTextToSpeechEngine()

    result = engine.synthesize("test", voice="en-us-neural", options={"pitch": 1.2})

    assert result.audio_bytes == b"test"


def test_fake_tts_voice_default_field_is_stored() -> None:
    engine = FakeTextToSpeechEngine(voice_default="en-us")

    assert engine.voice_default == "en-us"


def test_create_tts_engine_returns_fake_engine_for_fake_config() -> None:
    config = TextToSpeechConfig(engine="fake", voice="en-us")

    engine = create_tts_engine(config)

    assert isinstance(engine, FakeTextToSpeechEngine)
    assert engine.voice_default == "en-us"


def test_create_tts_engine_fake_with_no_voice_sets_none() -> None:
    config = TextToSpeechConfig(engine="fake")

    engine = create_tts_engine(config)

    assert isinstance(engine, FakeTextToSpeechEngine)
    assert engine.voice_default is None


def test_create_tts_engine_rejects_unsupported_engine() -> None:
    config = TextToSpeechConfig(engine="espeak")

    with pytest.raises(RuntimeError, match="espeak"):
        create_tts_engine(config)
