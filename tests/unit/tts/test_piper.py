"""Unit tests for the Piper TTS backend adapter."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from assistant_core.config.schema import TextToSpeechConfig
from assistant_core.interfaces import SynthesizedAudio, TextToSpeechEngine
from assistant_core.tts import PiperTextToSpeechEngine, create_tts_engine


def _make_piper_module(sample_rate: int = 22050, audio_chunks: list[bytes] | None = None) -> ModuleType:
    """Build a minimal stub of the piper module with a PiperVoice class."""
    if audio_chunks is None:
        audio_chunks = [b"\x00\x01\x02\x03"]

    module = ModuleType("piper")

    StubConfig = type("StubConfig", (), {"sample_rate": sample_rate})

    class StubPiperVoice:
        config = StubConfig()

        @staticmethod
        def load(model_path: str) -> "StubPiperVoice":
            return StubPiperVoice()

        def synthesize_stream_raw(
            self,
            text: str,
            *,
            length_scale: float | None = None,
        ):
            yield from audio_chunks  # type: ignore[misc]

    module.PiperVoice = StubPiperVoice  # type: ignore[attr-defined]
    return module


def test_piper_engine_is_protocol_compatible() -> None:
    engine = PiperTextToSpeechEngine(model_path="models/en_US-lessac-medium.onnx")

    assert isinstance(engine, TextToSpeechEngine)


def test_piper_engine_rejects_empty_model_path() -> None:
    with pytest.raises(ValueError, match="model_path"):
        PiperTextToSpeechEngine(model_path="")

    with pytest.raises(ValueError, match="model_path"):
        PiperTextToSpeechEngine(model_path="   ")


def test_piper_engine_load_and_synthesize_with_stubbed_dependency() -> None:
    engine = PiperTextToSpeechEngine(model_path="models/en_US-lessac-medium.onnx")
    module = _make_piper_module(sample_rate=22050, audio_chunks=[b"\x00\x01", b"\x02\x03"])

    original = sys.modules.get("piper")
    sys.modules["piper"] = module
    try:
        engine.load()
        result = engine.synthesize("hello world")

        assert isinstance(result, SynthesizedAudio)
        assert result.audio_bytes == b"\x00\x01\x02\x03"
        assert result.sample_rate_hz == 22050
        assert result.channels == 1
        assert result.sample_width_bytes == 2
        assert result.format == "pcm_s16le"
    finally:
        if original is None:
            sys.modules.pop("piper", None)
        else:
            sys.modules["piper"] = original


def test_piper_engine_lazy_load_on_first_synthesize() -> None:
    engine = PiperTextToSpeechEngine(model_path="models/en_US-lessac-medium.onnx")
    module = _make_piper_module(sample_rate=16000, audio_chunks=[b"\xAB\xCD"])

    original = sys.modules.get("piper")
    sys.modules["piper"] = module
    try:
        assert engine._voice is None

        result = engine.synthesize("lazy load test")

        assert engine._voice is not None
        assert result.audio_bytes == b"\xAB\xCD"
        assert result.sample_rate_hz == 16000
    finally:
        if original is None:
            sys.modules.pop("piper", None)
        else:
            sys.modules["piper"] = original


def test_piper_engine_passes_length_scale_from_options() -> None:
    engine = PiperTextToSpeechEngine(model_path="models/en_US-lessac-medium.onnx")

    call_args: dict[str, object] = {}

    module = ModuleType("piper")

    class StubConfig:
        sample_rate = 22050

    class StubPiperVoice:
        config = StubConfig()

        @staticmethod
        def load(model_path: str) -> "StubPiperVoice":
            return StubPiperVoice()

        def synthesize_stream_raw(self, text: str, *, length_scale: float | None = None):
            call_args["length_scale"] = length_scale
            yield b"\x00\x00"

    module.PiperVoice = StubPiperVoice  # type: ignore[attr-defined]

    original = sys.modules.get("piper")
    sys.modules["piper"] = module
    try:
        engine.synthesize("fast speech", options={"length_scale": 0.75})
        assert call_args.get("length_scale") == pytest.approx(0.75)
    finally:
        if original is None:
            sys.modules.pop("piper", None)
        else:
            sys.modules["piper"] = original


def test_piper_engine_raises_runtime_error_when_piper_not_installed() -> None:
    engine = PiperTextToSpeechEngine(model_path="models/en_US-lessac-medium.onnx")

    original = sys.modules.get("piper")
    sys.modules.pop("piper", None)

    # Temporarily block import by setting to None so importlib raises ImportError
    import builtins
    real_import = builtins.__import__

    def mock_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "piper":
            raise ImportError("No module named 'piper'")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = mock_import  # type: ignore[assignment]
    try:
        with pytest.raises(RuntimeError, match="piper-tts"):
            engine.load()
    finally:
        builtins.__import__ = real_import  # type: ignore[assignment]
        if original is not None:
            sys.modules["piper"] = original


def test_create_tts_engine_returns_piper_engine_for_piper_config() -> None:
    config = TextToSpeechConfig(engine="piper", model_path="models/en_US-lessac-medium.onnx")

    engine = create_tts_engine(config)

    assert isinstance(engine, PiperTextToSpeechEngine)
    assert engine.model_path == "models/en_US-lessac-medium.onnx"


def test_create_tts_engine_requires_model_path_for_piper() -> None:
    config = TextToSpeechConfig(engine="piper", model_path=None)

    with pytest.raises(RuntimeError, match="tts.model_path"):
        create_tts_engine(config)


def test_create_tts_engine_requires_non_empty_model_path_for_piper() -> None:
    config = TextToSpeechConfig(engine="piper", model_path="")

    with pytest.raises(RuntimeError, match="tts.model_path"):
        create_tts_engine(config)


def test_create_tts_engine_rejects_unsupported_engine_now_lists_piper() -> None:
    config = TextToSpeechConfig(engine="espeak")

    with pytest.raises(RuntimeError, match="espeak"):
        create_tts_engine(config)
