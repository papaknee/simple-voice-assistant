"""Tests for shared pytest fixture builders."""

from __future__ import annotations

from assistant_core.fakes import FakeSpeechToTextEngine
from tests.fixtures.runtime import build_runtime_harness


def test_runtime_harness_builder_allows_component_overrides() -> None:
    harness = build_runtime_harness(stt=FakeSpeechToTextEngine(transcript_text="fixture-text"))
    assert harness.stt.transcript_text == "fixture-text"
    assert harness.runtime.context.session_id == "session-1"
