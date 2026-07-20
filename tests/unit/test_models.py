"""Tests for assistant core typed data models."""

from __future__ import annotations

import pytest

from assistant_core.interfaces import SkillMetadata
from assistant_core.models import AssistantContext, IntentResolution, Transcript


def test_assistant_context_defaults() -> None:
    context = AssistantContext(session_id="session-1")
    assert context.session_id == "session-1"
    assert context.locale == "en-US"
    assert context.turn_id is None
    assert context.metadata == {}


def test_transcript_confidence_accepts_valid_range() -> None:
    transcript = Transcript(text="turn on lights", confidence=0.85)
    assert transcript.confidence == pytest.approx(0.85)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_transcript_confidence_rejects_invalid_range(confidence: float) -> None:
    with pytest.raises(ValueError, match="Transcript confidence"):
        Transcript(text="bad confidence", confidence=confidence)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_intent_resolution_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="Intent confidence"):
        IntentResolution(intent_name="set_timer", confidence=confidence)


def test_skill_metadata_defaults() -> None:
    metadata = SkillMetadata(name="echo_debug", description="Echo input")

    assert metadata.version == "0.1.0"
    assert metadata.example_utterances == ()
    assert metadata.tags == ()
    assert metadata.config_schema == {}
    assert metadata.response_contract == {}
