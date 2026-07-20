"""Text-to-speech adapter shell and deterministic fake engine."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from assistant_core.config.schema import TextToSpeechConfig
from assistant_core.interfaces import SynthesizedAudio, TextToSpeechEngine
from assistant_core.models import JsonValue


@dataclass(slots=True)
class FakeTextToSpeechEngine(TextToSpeechEngine):
    """Deterministic fake TTS engine for tests and offline runtime wiring."""

    sample_rate_hz: int = 22050
    channels: int = 1
    sample_width_bytes: int = 2
    voice_default: str | None = None
    backend_name: str = "fake"

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> SynthesizedAudio:
        _ = options
        return SynthesizedAudio(
            audio_bytes=text.encode("utf-8"),
            sample_rate_hz=self.sample_rate_hz,
            channels=self.channels,
            sample_width_bytes=self.sample_width_bytes,
            format="pcm_s16le",
        )


@dataclass(slots=True)
class PiperTextToSpeechEngine(TextToSpeechEngine):
    """Local offline TTS backend backed by Piper neural text-to-speech.

    Piper uses ONNX-backed neural voice models and runs fully on-device.
    The model is loaded lazily on first call to ``synthesize`` or explicitly
    via ``load()``. Each voice model is a pair of files: ``<name>.onnx`` and
    ``<name>.onnx.json``.
    """

    model_path: str
    backend_name: str = "piper"
    _voice: object | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.model_path.strip():
            raise ValueError("model_path must be a non-empty string.")

    def load(self) -> None:
        """Load the Piper voice model. Called lazily by synthesize if not already loaded."""
        try:
            module = importlib.import_module("piper")
        except ImportError as exc:
            raise RuntimeError(
                "piper-tts dependency is not installed. Install optional dependencies: "
                "`pip install simple-voice-assistant[tts]`."
            ) from exc

        voice_class = getattr(module, "PiperVoice", None)
        if voice_class is None:
            raise RuntimeError("piper.PiperVoice is not available in the installed package.")

        self._voice = voice_class.load(self.model_path)

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> SynthesizedAudio:
        """Synthesize speech from text using the loaded Piper voice model."""
        _ = voice
        if self._voice is None:
            self.load()

        piper_voice = self._voice
        length_scale: float | None = None
        if isinstance(options, dict) and isinstance(options.get("length_scale"), (int, float)):
            length_scale = float(options["length_scale"])

        audio_bytes = b"".join(
            piper_voice.synthesize_stream_raw(  # type: ignore[union-attr]
                text,
                length_scale=length_scale,
            )
        )

        sample_rate_hz: int = piper_voice.config.sample_rate  # type: ignore[union-attr]

        return SynthesizedAudio(
            audio_bytes=audio_bytes,
            sample_rate_hz=sample_rate_hz,
            channels=1,
            sample_width_bytes=2,
            format="pcm_s16le",
        )


@dataclass(slots=True)
class CachingTextToSpeechEngine(TextToSpeechEngine):
    """LRU in-memory cache wrapper for any TextToSpeechEngine.

    Caches synthesized audio by ``(text, voice)`` key so repeated calls for the
    same text avoid re-running the underlying synthesis. The cache is bounded by
    ``max_entries``; when full, the least-recently-used entry is evicted.

    Note: ``options`` are forwarded to the inner engine on cache misses but are
    *not* included in the cache key.  Callers that rely on varying options for
    the same text should bypass the cache or use a fresh instance.
    """

    engine: TextToSpeechEngine
    max_entries: int = 64
    _cache: dict[tuple[str, str | None], SynthesizedAudio] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be >= 1.")

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> SynthesizedAudio:
        key = (text, voice)
        cached = self._cache.get(key)
        if cached is not None:
            # Refresh recency: move to end of insertion order.
            del self._cache[key]
            self._cache[key] = cached
            return cached

        result = self.engine.synthesize(text, voice=voice, options=options)

        if len(self._cache) >= self.max_entries:
            # Evict least-recently-used (oldest insertion-order entry).
            self._cache.pop(next(iter(self._cache)))

        self._cache[key] = result
        return result

    def cache_size(self) -> int:
        """Return the number of entries currently in the cache."""
        return len(self._cache)

    def clear_cache(self) -> None:
        """Evict all cached entries."""
        self._cache.clear()


def create_tts_engine(config: TextToSpeechConfig) -> TextToSpeechEngine:
    """Create the configured text-to-speech engine.

    Supported engines:
    - ``"fake"``: deterministic in-memory fake for tests and runtime wiring.
    - ``"piper"``: local offline neural TTS via Piper (requires ``tts`` extras).

    When ``config.cache_enabled`` is ``True`` the returned engine is wrapped in
    a :class:`CachingTextToSpeechEngine` with the configured max entry count.
    """
    if config.engine == "fake":
        engine: TextToSpeechEngine = FakeTextToSpeechEngine(voice_default=config.voice)
    elif config.engine == "piper":
        if config.model_path is None or not config.model_path.strip():
            raise RuntimeError("tts.model_path must be set when tts.engine='piper'.")
        engine = PiperTextToSpeechEngine(model_path=config.model_path)
    else:
        raise RuntimeError(
            f"Text-to-speech engine '{config.engine}' is not supported. "
            "Available engines: 'fake', 'piper'."
        )

    if config.cache_enabled:
        return CachingTextToSpeechEngine(engine=engine, max_entries=config.cache_max_entries)

    return engine

