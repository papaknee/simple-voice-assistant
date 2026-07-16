"""Smoke tests for baseline project tooling."""

import assistant_core


def test_assistant_core_exposes_expected_subpackages() -> None:
    assert sorted(assistant_core.__all__) == [
        "audio",
        "intent",
        "models",
        "runtime",
        "skills",
        "stt",
        "tts",
        "vad",
        "wake",
    ]
