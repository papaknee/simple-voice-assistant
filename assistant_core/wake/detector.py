"""Wake-word detector adapter with threshold and cooldown enforcement."""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field

from assistant_core.config.schema import WakeWordConfig
from assistant_core.interfaces import WakeDetection, WakeWordDetector
from assistant_core.models import JsonValue


@dataclass(slots=True)
class OpenWakeWordDetector:
    """Local wake-word detector adapter backed by the openWakeWord package."""

    model_path: str
    _model: object | None = field(default=None, init=False)

    def load(self) -> None:
        """Load the openWakeWord model lazily to keep startup lightweight."""
        try:
            model_module = importlib.import_module("openwakeword.model")
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword dependency is not installed. "
                "Install optional dependencies: `pip install simple-voice-assistant[wake]`."
            ) from exc

        model_factory = getattr(model_module, "Model", None)
        if model_factory is None:
            raise RuntimeError("openwakeword.model.Model is not available in the installed package.")

        self._model = model_factory(wakeword_models=[self.model_path])

    def reset(self) -> None:
        """Release model reference so the detector can be re-loaded cleanly."""
        self._model = None

    def process_frame(self, frame: bytes) -> WakeDetection:
        """Process a PCM frame and return a normalized wake detection result."""
        if self._model is None:
            raise RuntimeError("OpenWakeWordDetector must be loaded before processing frames.")

        predict = getattr(self._model, "predict", None)
        if predict is None:
            raise RuntimeError("openwakeword model does not expose a predict(frame) method.")

        raw_result = predict(frame)
        scores = self._normalize_scores(raw_result)
        if not scores:
            return WakeDetection(detected=False, score=0.0)

        label, score = max(scores.items(), key=lambda item: item[1])
        return WakeDetection(
            detected=score > 0.0,
            score=score,
            metadata={"wakeword_label": label},
        )

    def detection_metadata(self) -> dict[str, JsonValue]:
        """Expose detector metadata for diagnostics and runtime events."""
        return {
            "engine": "openwakeword",
            "model_path": self.model_path,
        }

    @staticmethod
    def _normalize_scores(raw_result: object) -> dict[str, float]:
        """Normalize openWakeWord predictions to a label->score mapping."""
        if isinstance(raw_result, dict):
            normalized: dict[str, float] = {}
            for label, score in raw_result.items():
                if isinstance(score, (int, float)):
                    normalized[str(label)] = float(score)
            return normalized
        if isinstance(raw_result, (int, float)):
            return {"wakeword": float(raw_result)}
        return {}


@dataclass(slots=True)
class ConfiguredWakeWordDetector:
    """Wraps any WakeWordDetector and enforces score threshold and activation cooldown.

    This adapter sits between the raw backend detector and the runtime, applying
    two post-processing policies:
    - **Threshold**: Detections with a score below ``sensitivity`` are suppressed.
    - **Cooldown**: Detections are suppressed for ``cooldown_seconds`` after any
      accepted detection, preventing rapid re-triggering.
    """

    inner: WakeWordDetector
    sensitivity: float = 0.5
    cooldown_seconds: float = 1.0
    _last_detection_time: float | None = field(default=None, init=False)

    def load(self) -> None:
        """Delegate model loading to the inner detector."""
        self.inner.load()

    def reset(self) -> None:
        """Delegate reset to the inner detector and clear cooldown state."""
        self.inner.reset()
        self._last_detection_time = None

    def process_frame(self, frame: bytes) -> WakeDetection:
        """Process a PCM frame, applying threshold and cooldown filtering."""
        result = self.inner.process_frame(frame)

        if not result.detected:
            return result

        # Apply score threshold: suppress if score is present but below sensitivity.
        if result.score is not None and result.score < self.sensitivity:
            return WakeDetection(detected=False, score=result.score, metadata=result.metadata)

        # Apply cooldown: suppress if a detection was accepted within the cooldown window.
        now = time.monotonic()
        if self._last_detection_time is not None:
            elapsed = now - self._last_detection_time
            if elapsed < self.cooldown_seconds:
                return WakeDetection(detected=False, score=result.score, metadata=result.metadata)

        self._last_detection_time = now
        return result

    def detection_metadata(self) -> dict[str, JsonValue]:
        """Return inner metadata merged with threshold and cooldown configuration."""
        base = self.inner.detection_metadata()
        return {
            **base,
            "sensitivity": self.sensitivity,
            "cooldown_seconds": self.cooldown_seconds,
        }


def create_wake_detector(config: WakeWordConfig) -> WakeWordDetector:
    """Build and return a wake-word detector from the provided configuration.

    The returned detector is always wrapped in a :class:`ConfiguredWakeWordDetector`
    to enforce threshold and cooldown policies from ``config``.

    Supported engines:
    - ``"fake"`` — :class:`~assistant_core.fakes.FakeWakeWordDetector` for tests and
      offline development without a real wake-word model.
        - ``"openwakeword"`` — local detector backend using the openWakeWord package.

    Raises:
        AssistantError: If the engine name is not supported or if a required optional
            dependency is not installed.
    """
    if config.engine == "fake":
        from assistant_core.fakes import FakeWakeWordDetector

        inner: WakeWordDetector = FakeWakeWordDetector()
        return ConfiguredWakeWordDetector(
            inner=inner,
            sensitivity=config.sensitivity,
            cooldown_seconds=config.activation_cooldown_seconds,
        )

    if config.engine == "openwakeword":
        if config.model_path is None or not config.model_path.strip():
            raise RuntimeError(
                "wake.model_path must be set when wake.engine='openwakeword'."
            )

        inner = OpenWakeWordDetector(model_path=config.model_path)
        return ConfiguredWakeWordDetector(
            inner=inner,
            sensitivity=config.sensitivity,
            cooldown_seconds=config.activation_cooldown_seconds,
        )

    raise RuntimeError(
        f"Wake-word engine '{config.engine}' is not supported. "
        "Available engines: 'fake', 'openwakeword'."
    )
