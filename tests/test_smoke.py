"""Smoke tests for baseline project tooling."""

import assistant_core


def test_assistant_core_exposes_expected_subpackages() -> None:
    assert sorted(assistant_core.__all__) == [
        "audio",
        "fakes",
        "intent",
        "interfaces",
        "models",
        "runtime",
        "skills",
        "stt",
        "tts",
        "vad",
        "wake",
    ]
