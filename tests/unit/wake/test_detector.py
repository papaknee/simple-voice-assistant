"""Unit tests for the wake-word detector adapter and factory."""

from __future__ import annotations

import sys
import time
from types import ModuleType

import pytest

from assistant_core.config.schema import WakeWordConfig
from assistant_core.fakes import FakeWakeWordDetector
from assistant_core.interfaces import WakeDetection
from assistant_core.wake.detector import ConfiguredWakeWordDetector, OpenWakeWordDetector, create_wake_detector


# ---------------------------------------------------------------------------
# ConfiguredWakeWordDetector — threshold behaviour
# ---------------------------------------------------------------------------


def test_detection_passes_through_at_or_above_sensitivity() -> None:
    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5)
    inner.load()

    result = adapter.process_frame(b"wake")

    assert result.detected is True


def test_threshold_suppresses_detection_below_sensitivity() -> None:
    inner = FakeWakeWordDetector(wake_frame=b"wake", score=0.3)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5)
    inner.load()

    result = adapter.process_frame(b"wake")

    assert result.detected is False
    assert result.score == pytest.approx(0.3)


def test_detection_without_score_is_not_suppressed_by_threshold() -> None:
    """Detections with score=None bypass the threshold check."""
    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    # Force the inner to return None score by subclassing in a local stub
    inner.score = 1.0  # type: ignore[attr-defined]

    class NoScoreDetector:
        def load(self) -> None: ...
        def reset(self) -> None: ...

        def process_frame(self, frame: bytes) -> WakeDetection:
            if frame == b"wake":
                return WakeDetection(detected=True, score=None)
            return WakeDetection(detected=False, score=None)

        def detection_metadata(self) -> dict:
            return {}

    adapter = ConfiguredWakeWordDetector(inner=NoScoreDetector(), sensitivity=0.9)  # type: ignore[arg-type]

    result = adapter.process_frame(b"wake")

    assert result.detected is True


def test_non_detection_passes_through_without_modification() -> None:
    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5)
    inner.load()

    result = adapter.process_frame(b"other")

    assert result.detected is False


# ---------------------------------------------------------------------------
# ConfiguredWakeWordDetector — cooldown behaviour
# ---------------------------------------------------------------------------


def test_cooldown_suppresses_second_detection_within_window(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5, cooldown_seconds=2.0)
    inner.load()

    # First detection at t=0 should be accepted.
    first = adapter.process_frame(b"wake")
    assert first.detected is True

    # Advance clock inside cooldown window; detection should be suppressed.
    clock[0] = 1.5
    second = adapter.process_frame(b"wake")
    assert second.detected is False


def test_cooldown_allows_detection_after_window_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5, cooldown_seconds=2.0)
    inner.load()

    adapter.process_frame(b"wake")  # accepted at t=0

    # Advance past the cooldown window.
    clock[0] = 2.1
    result = adapter.process_frame(b"wake")
    assert result.detected is True


def test_cooldown_does_not_apply_before_any_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    # Long cooldown; shouldn't affect first detection.
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5, cooldown_seconds=100.0)
    inner.load()

    result = adapter.process_frame(b"wake")
    assert result.detected is True


# ---------------------------------------------------------------------------
# ConfiguredWakeWordDetector — load / reset / metadata
# ---------------------------------------------------------------------------


def test_load_delegates_to_inner_detector() -> None:
    inner = FakeWakeWordDetector(wake_frame=b"wake")
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5)

    assert inner._loaded is False
    adapter.load()
    assert inner._loaded is True


def test_reset_delegates_to_inner_and_clears_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])

    inner = FakeWakeWordDetector(wake_frame=b"wake", score=1.0)
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.5, cooldown_seconds=10.0)
    inner.load()

    # Accept first detection to set cooldown timestamp.
    adapter.process_frame(b"wake")
    assert adapter._last_detection_time is not None

    # Reset should clear cooldown state and unload the inner detector.
    adapter.reset()

    assert adapter._last_detection_time is None
    assert inner._loaded is False


def test_detection_metadata_includes_config_values() -> None:
    inner = FakeWakeWordDetector(wake_frame=b"wake")
    adapter = ConfiguredWakeWordDetector(inner=inner, sensitivity=0.7, cooldown_seconds=3.0)

    metadata = adapter.detection_metadata()

    assert metadata["sensitivity"] == pytest.approx(0.7)
    assert metadata["cooldown_seconds"] == pytest.approx(3.0)
    # Inner fake metadata should also be present.
    assert metadata["engine"] == "fake"


# ---------------------------------------------------------------------------
# create_wake_detector factory
# ---------------------------------------------------------------------------


def test_factory_returns_configured_detector_for_fake_engine() -> None:
    config = WakeWordConfig(engine="fake", sensitivity=0.6, activation_cooldown_seconds=1.5)

    detector = create_wake_detector(config)

    assert isinstance(detector, ConfiguredWakeWordDetector)
    assert detector.sensitivity == pytest.approx(0.6)
    assert detector.cooldown_seconds == pytest.approx(1.5)
    assert isinstance(detector.inner, FakeWakeWordDetector)


def test_factory_raises_for_unsupported_engine() -> None:
    config = WakeWordConfig(engine="unknown_engine")

    with pytest.raises(RuntimeError, match="unknown_engine"):
        create_wake_detector(config)


def test_factory_raises_when_openwakeword_model_path_missing() -> None:
    config = WakeWordConfig(engine="openwakeword", model_path="")

    with pytest.raises(RuntimeError, match="wake.model_path"):
        create_wake_detector(config)


def test_factory_returns_configured_detector_for_openwakeword_engine() -> None:
    config = WakeWordConfig(
        engine="openwakeword",
        model_path="models/hey_assistant.onnx",
        sensitivity=0.77,
        activation_cooldown_seconds=2.25,
    )

    detector = create_wake_detector(config)

    assert isinstance(detector, ConfiguredWakeWordDetector)
    assert detector.sensitivity == pytest.approx(0.77)
    assert detector.cooldown_seconds == pytest.approx(2.25)
    assert isinstance(detector.inner, OpenWakeWordDetector)


def test_openwakeword_detector_load_raises_when_dependency_missing() -> None:
    detector = OpenWakeWordDetector(model_path="models/hey_assistant.onnx")

    original_module = sys.modules.pop("openwakeword.model", None)
    original_package = sys.modules.pop("openwakeword", None)
    try:
        with pytest.raises(RuntimeError, match="openwakeword dependency is not installed"):
            detector.load()
    finally:
        if original_module is not None:
            sys.modules["openwakeword.model"] = original_module
        if original_package is not None:
            sys.modules["openwakeword"] = original_package


def test_openwakeword_detector_process_and_metadata_with_stubbed_dependency() -> None:
    detector = OpenWakeWordDetector(model_path="models/hey_assistant.onnx")

    class StubModel:
        def __init__(self, wakeword_models: list[str]) -> None:
            self.wakeword_models = wakeword_models

        def predict(self, frame: bytes) -> dict[str, float]:
            if frame == b"wake":
                return {"hey_assistant": 0.88}
            return {"hey_assistant": 0.05}

    model_module = ModuleType("openwakeword.model")
    model_module.Model = StubModel  # type: ignore[attr-defined]
    package_module = ModuleType("openwakeword")

    original_module = sys.modules.get("openwakeword.model")
    original_package = sys.modules.get("openwakeword")
    sys.modules["openwakeword.model"] = model_module
    sys.modules["openwakeword"] = package_module
    try:
        detector.load()

        wake_result = detector.process_frame(b"wake")
        assert wake_result.detected is True
        assert wake_result.score == pytest.approx(0.88)
        assert wake_result.metadata["wakeword_label"] == "hey_assistant"

        silence_result = detector.process_frame(b"other")
        assert silence_result.detected is True
        assert silence_result.score == pytest.approx(0.05)

        metadata = detector.detection_metadata()
        assert metadata["engine"] == "openwakeword"
        assert metadata["model_path"] == "models/hey_assistant.onnx"

        detector.reset()
        with pytest.raises(RuntimeError, match="must be loaded"):
            detector.process_frame(b"wake")
    finally:
        if original_module is not None:
            sys.modules["openwakeword.model"] = original_module
        else:
            sys.modules.pop("openwakeword.model", None)
        if original_package is not None:
            sys.modules["openwakeword"] = original_package
        else:
            sys.modules.pop("openwakeword", None)


def test_factory_fake_detector_is_functional_after_load() -> None:
    config = WakeWordConfig(engine="fake", sensitivity=0.5)
    detector = create_wake_detector(config)

    detector.load()
    inner = detector.inner  # type: ignore[attr-defined]
    # Inject a known wake frame so the fake triggers.
    inner.wake_frame = b"hello"
    inner.score = 1.0

    result = detector.process_frame(b"hello")

    assert result.detected is True


def test_factory_respects_sensitivity_from_config() -> None:
    config = WakeWordConfig(engine="fake", sensitivity=0.9)
    detector = create_wake_detector(config)
    detector.load()

    inner = detector.inner  # type: ignore[attr-defined]
    inner.wake_frame = b"hello"
    inner.score = 0.5  # below sensitivity threshold

    result = detector.process_frame(b"hello")

    assert result.detected is False
