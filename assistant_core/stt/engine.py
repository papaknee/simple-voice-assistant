"""Speech-to-text adapter shell and deterministic fake engine."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field

from assistant_core.config.schema import SpeechToTextConfig
from assistant_core.interfaces import SpeechToTextEngine
from assistant_core.models import CapturedAudio, JsonValue, Transcript


@dataclass(slots=True)
class FakeSpeechToTextEngine(SpeechToTextEngine):
    """Deterministic fake STT engine for tests and offline runtime wiring."""

    transcript_text: str = "hello"
    confidence: float = 1.0
    language_default: str = "en-US"
    backend_name: str = "fake"
    warnings: tuple[str, ...] = ()

    def transcribe(
        self,
        audio_bytes: bytes,
        audio: CapturedAudio,
        *,
        language: str | None = None,
        options: dict[str, object] | None = None,
    ) -> Transcript:
        _ = (audio_bytes, options)
        return Transcript(
            text=self.transcript_text,
            language=language or self.language_default,
            confidence=self.confidence,
            duration_seconds=audio.duration_seconds,
            metadata={
                "backend_name": self.backend_name,
                "warnings": list(self.warnings),
                "audio_frame_count": audio.frame_count,
                "audio_source": audio.source,
            },
        )


@dataclass(slots=True)
class VoskSpeechToTextEngine(SpeechToTextEngine):
    """Local STT backend adapter backed by the Vosk package."""

    model_path: str
    language: str = "en-US"
    backend_name: str = "vosk"
    low_confidence_threshold: float = 0.5
    _model: object | None = field(default=None, init=False, repr=False)
    _module: object | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.model_path.strip():
            raise ValueError("model_path must be a non-empty string.")
        if not self.language.strip():
            raise ValueError("language must be a non-empty string.")
        if not 0.0 <= self.low_confidence_threshold <= 1.0:
            raise ValueError("low_confidence_threshold must be between 0.0 and 1.0.")

    def load(self) -> None:
        """Load the Vosk model lazily to keep startup time minimal."""
        try:
            module = importlib.import_module("vosk")
        except ImportError as exc:
            raise RuntimeError(
                "vosk dependency is not installed. Install optional dependencies: "
                "`pip install simple-voice-assistant[stt]`."
            ) from exc

        model_factory = getattr(module, "Model", None)
        if model_factory is None:
            raise RuntimeError("vosk.Model is not available in the installed package.")

        self._module = module
        self._model = model_factory(self.model_path)

    def reset(self) -> None:
        self._model = None
        self._module = None

    def transcribe(
        self,
        audio_bytes: bytes,
        audio: CapturedAudio,
        *,
        language: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> Transcript:
        module = self._ensure_loaded()
        requested_language = language or self.language
        self._ensure_supported_language(requested_language)

        warnings: list[str] = []
        if audio.sample_rate_hz <= 0:
            raise RuntimeError("Captured audio must have a positive sample rate.")

        if not audio_bytes:
            warnings.append("empty_audio")
            return self._build_transcript(
                text="",
                language=requested_language,
                audio=audio,
                confidence=0.0,
                warnings=warnings,
            )

        recognizer_factory = getattr(module, "KaldiRecognizer", None)
        if recognizer_factory is None:
            raise RuntimeError("vosk.KaldiRecognizer is not available in the installed package.")

        recognizer = recognizer_factory(self._model, audio.sample_rate_hz)
        accept_waveform = getattr(recognizer, "AcceptWaveform", None)
        if accept_waveform is None:
            raise RuntimeError("vosk recognizer does not expose AcceptWaveform(audio_bytes).")

        accepted = bool(accept_waveform(audio_bytes))
        raw_result = self._read_recognizer_result(recognizer, accepted)
        text, confidence, result_warnings = self._parse_result(raw_result)
        warnings.extend(result_warnings)

        if not text:
            warnings.append("silence")
            return self._build_transcript(
                text="",
                language=requested_language,
                audio=audio,
                confidence=0.0,
                warnings=warnings,
            )

        if confidence is not None and confidence < self.low_confidence_threshold:
            warnings.append("low_confidence")

        return self._build_transcript(
            text=text,
            language=requested_language,
            audio=audio,
            confidence=confidence,
            warnings=warnings,
        )

    def _ensure_loaded(self) -> object:
        if self._model is None or self._module is None:
            self.load()
        if self._module is None or self._model is None:
            raise RuntimeError("VoskSpeechToTextEngine failed to load its backend model.")
        return self._module

    def _ensure_supported_language(self, requested_language: str) -> None:
        configured = self._language_key(self.language)
        requested = self._language_key(requested_language)
        if requested != configured:
            raise RuntimeError(
                f"VoskSpeechToTextEngine is configured for language '{self.language}' "
                f"but received unsupported language '{requested_language}'."
            )

    def _read_recognizer_result(self, recognizer: object, accepted: bool) -> str:
        result_method_name = "Result" if accepted else "FinalResult"
        result_method = getattr(recognizer, result_method_name, None)
        if result_method is None:
            raise RuntimeError(f"vosk recognizer does not expose {result_method_name}().")
        return str(result_method())

    def _parse_result(self, raw_result: str) -> tuple[str, float | None, list[str]]:
        try:
            parsed = json.loads(raw_result)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"vosk returned invalid JSON transcription payload: {exc}") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("vosk transcription payload must be a JSON object.")

        text = str(parsed.get("text", "")).strip()
        confidence = self._extract_confidence(parsed)
        warnings: list[str] = []
        if confidence is not None and confidence < self.low_confidence_threshold:
            warnings.append("low_confidence")
        return text, confidence, warnings

    def _build_transcript(
        self,
        *,
        text: str,
        language: str,
        audio: CapturedAudio,
        confidence: float | None,
        warnings: list[str],
    ) -> Transcript:
        metadata: dict[str, JsonValue] = {
            "backend_name": self.backend_name,
            "model_path": self.model_path,
            "warnings": warnings,
            "audio_frame_count": audio.frame_count,
            "audio_source": audio.source,
        }
        return Transcript(
            text=text,
            language=language,
            confidence=confidence,
            duration_seconds=audio.duration_seconds,
            metadata=metadata,
        )

    @staticmethod
    def _extract_confidence(parsed: dict[str, object]) -> float | None:
        if isinstance(parsed.get("confidence"), (int, float)):
            return float(parsed["confidence"])

        result = parsed.get("result")
        if not isinstance(result, list) or not result:
            return None

        confidences: list[float] = []
        for item in result:
            if isinstance(item, dict) and isinstance(item.get("conf"), (int, float)):
                confidences.append(float(item["conf"]))
        if not confidences:
            return None
        return sum(confidences) / len(confidences)

    @staticmethod
    def _language_key(language: str) -> str:
        return language.split("-", maxsplit=1)[0].strip().lower()


def create_stt_engine(config: SpeechToTextConfig) -> SpeechToTextEngine:
    """Create the configured speech-to-text engine.

    The STT shell currently exposes the deterministic fake engine so the runtime
    and tests can be wired without optional backend dependencies. Additional
    backends will be added behind this factory as separate adapters.
    """
    if config.engine == "fake":
        return FakeSpeechToTextEngine(language_default=config.language)

    if config.engine == "vosk":
        if config.model_path is None or not config.model_path.strip():
            raise RuntimeError("stt.model_path must be set when stt.engine='vosk'.")
        return VoskSpeechToTextEngine(model_path=config.model_path, language=config.language)

    raise RuntimeError(
        f"Speech-to-text engine '{config.engine}' is not supported. "
        "Available engines: 'fake', 'vosk'."
    )