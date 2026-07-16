"""Runtime state and event types for the assistant state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from assistant_core.models import AssistantError, JsonValue


class RuntimeState(StrEnum):
    """Canonical runtime states for orchestration."""

    BOOT = "boot"
    IDLE_LISTENING = "idle_listening"
    ACTIVATED = "activated"
    CAPTURING_COMMAND = "capturing_command"
    TRANSCRIBING = "transcribing"
    ROUTING_INTENT = "routing_intent"
    EXECUTING_SKILL = "executing_skill"
    RESPONDING = "responding"
    RECOVERING = "recovering"
    SHUTDOWN = "shutdown"


class RuntimeEventType(StrEnum):
    """Event categories emitted by runtime lifecycle operations."""

    STATE_TRANSITIONED = "state_transitioned"
    WAKE_DETECTED = "wake_detected"
    COMMAND_CAPTURE_STARTED = "command_capture_started"
    COMMAND_CAPTURE_COMPLETED = "command_capture_completed"
    TRANSCRIPTION_COMPLETED = "transcription_completed"
    INTENT_ROUTED = "intent_routed"
    SKILL_EXECUTED = "skill_executed"
    RESPONSE_RENDERED = "response_rendered"
    ERROR_RAISED = "error_raised"
    RECOVERY_COMPLETED = "recovery_completed"
    SHUTDOWN_COMPLETED = "shutdown_completed"


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    """Structured runtime event for logging, diagnostics, and event bus dispatch."""

    event_type: RuntimeEventType
    state: RuntimeState
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))
    turn_id: str | None = None
    duration_ms: float | None = None
    payload: dict[str, JsonValue] = field(default_factory=dict)
    error: AssistantError | None = None

    def __post_init__(self) -> None:
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("Runtime event duration_ms cannot be negative.")
