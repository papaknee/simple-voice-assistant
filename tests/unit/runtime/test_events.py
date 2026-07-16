"""Tests for runtime state and event models."""

from __future__ import annotations

from datetime import UTC

import pytest
from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType, RuntimeState


def test_runtime_event_defaults() -> None:
    event = RuntimeEvent(
        event_type=RuntimeEventType.WAKE_DETECTED,
        state=RuntimeState.IDLE_LISTENING,
    )
    assert event.event_id
    assert event.occurred_at.tzinfo == UTC
    assert event.payload == {}
    assert event.error is None


def test_runtime_event_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="duration_ms"):
        RuntimeEvent(
            event_type=RuntimeEventType.TRANSCRIPTION_COMPLETED,
            state=RuntimeState.TRANSCRIBING,
            duration_ms=-1.0,
        )
