"""Unit tests for the Vosk STT backend adapter."""

from __future__ import annotations

import sys
from types import ModuleType

import pytest

from assistant_core.config.schema import SpeechToTextConfig
from assistant_core.stt import VoskSpeechToTextEngine, create_stt_engine
from assistant_core.models import CapturedAudio


def test_create_stt_engine_returns_vosk_engine_for_vosk_config() -> None:
    config = SpeechToTextConfig(engine="vosk", model_path="models/vosk-en", language="en-US")

    engine = create_stt_engine(config)

    assert isinstance(engine, VoskSpeechToTextEngine)
    assert engine.model_path == "models/vosk-en"
    assert engine.language == "en-US"


def test_create_stt_engine_requires_model_path_for_vosk() -> None:
    config = SpeechToTextConfig(engine="vosk", model_path=None)

    with pytest.raises(RuntimeError, match="stt.model_path"):
        create_stt_engine(config)


def test_vosk_engine_load_and_transcribe_with_stubbed_dependency() -> None:
    engine = VoskSpeechToTextEngine(model_path="models/vosk-en", language="en-US")

    class StubModel:
        def __init__(self, model_path: str) -> None:
            self.model_path = model_path

    class StubRecognizer:
        def __init__(self, model: object, sample_rate_hz: int) -> None:
            self.model = model
            self.sample_rate_hz = sample_rate_hz
            self.frames: list[bytes] = []

        def AcceptWaveform(self, frame: bytes) -> bool:
            self.frames.append(frame)
            return True

        def Result(self) -> str:
            return (
                '{"text": "turn on lights", "result": [{"conf": 0.84}, {"conf": 0.9}]}'
            )

        def FinalResult(self) -> str:
            return self.Result()

    module = ModuleType("vosk")
    module.Model = StubModel  # type: ignore[attr-defined]
    module.KaldiRecognizer = StubRecognizer  # type: ignore[attr-defined]

    original_module = sys.modules.get("vosk")
    sys.modules["vosk"] = module
    try:
        engine.load()

        transcript = engine.transcribe(
            b"\x00\x01",
            CapturedAudio(
                sample_rate_hz=16000,
                channels=1,
                sample_width_bytes=2,
                frame_count=8000,
                duration_seconds=0.5,
                source="microphone-1",
            ),
        )

        assert transcript.text == "turn on lights"
        assert transcript.language == "en-US"
        assert transcript.confidence == pytest.approx(0.87)
        assert transcript.metadata["backend_name"] == "vosk"
        assert transcript.metadata["model_path"] == "models/vosk-en"
        assert transcript.metadata["warnings"] == []
    finally:
        if original_module is None:
            sys.modules.pop("vosk", None)
        else:
            sys.modules["vosk"] = original_module


def test_vosk_engine_returns_empty_transcript_for_empty_audio() -> None:
    engine = VoskSpeechToTextEngine(model_path="models/vosk-en")

    class StubModel:
        def __init__(self, model_path: str) -> None:
            self.model_path = model_path

    class StubRecognizer:
        def __init__(self, model: object, sample_rate_hz: int) -> None:
            self.model = model
            self.sample_rate_hz = sample_rate_hz

        def AcceptWaveform(self, frame: bytes) -> bool:
            return False

        def Result(self) -> str:
            return '{"text": "spoken command"}'

        def FinalResult(self) -> str:
            return self.Result()

    module = ModuleType("vosk")
    module.Model = StubModel  # type: ignore[attr-defined]
    module.KaldiRecognizer = StubRecognizer  # type: ignore[attr-defined]

    original_module = sys.modules.get("vosk")
    sys.modules["vosk"] = module
    try:
        engine.load()

        transcript = engine.transcribe(
            b"",
            CapturedAudio(
                sample_rate_hz=16000,
                channels=1,
                sample_width_bytes=2,
                frame_count=0,
                duration_seconds=0.0,
            ),
        )

        assert transcript.text == ""
        assert transcript.confidence == 0.0
        assert transcript.metadata["warnings"] == ["empty_audio"]
    finally:
        if original_module is None:
            sys.modules.pop("vosk", None)
        else:
            sys.modules["vosk"] = original_module


def test_vosk_engine_rejects_unsupported_language() -> None:
    engine = VoskSpeechToTextEngine(model_path="models/vosk-en", language="en-US")

    class StubModel:
        def __init__(self, model_path: str) -> None:
            self.model_path = model_path

    class StubRecognizer:
        def __init__(self, model: object, sample_rate_hz: int) -> None:
            self.model = model
            self.sample_rate_hz = sample_rate_hz

        def AcceptWaveform(self, frame: bytes) -> bool:
            return True

        def Result(self) -> str:
            return '{"text": "bonjour"}'

        def FinalResult(self) -> str:
            return self.Result()

    module = ModuleType("vosk")
    module.Model = StubModel  # type: ignore[attr-defined]
    module.KaldiRecognizer = StubRecognizer  # type: ignore[attr-defined]

    original_module = sys.modules.get("vosk")
    sys.modules["vosk"] = module
    try:
        engine.load()

        with pytest.raises(RuntimeError, match="unsupported language"):
            engine.transcribe(
                b"\x00",
                CapturedAudio(
                    sample_rate_hz=16000,
                    channels=1,
                    sample_width_bytes=2,
                    frame_count=8000,
                    duration_seconds=0.5,
                ),
                language="fr-FR",
            )
    finally:
        if original_module is None:
            sys.modules.pop("vosk", None)
        else:
            sys.modules["vosk"] = original_module
