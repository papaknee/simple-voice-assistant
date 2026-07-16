"""Core typed data models shared across assistant runtime stages."""

from __future__ import annotations

from dataclasses import dataclass, field

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]


@dataclass(frozen=True, slots=True)
class AssistantContext:
    """Per-turn runtime context shared between pipeline stages."""

    session_id: str
    locale: str = "en-US"
    turn_id: str | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CapturedAudio:
    """Description of buffered command audio prepared for STT."""

    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    duration_seconds: float
    source: str | None = None


@dataclass(frozen=True, slots=True)
class Transcript:
    """Normalized STT output with optional confidence metadata."""

    text: str
    language: str | None = None
    confidence: float | None = None
    duration_seconds: float | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Transcript confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class IntentResolution:
    """Intent routing decision from a transcript."""

    intent_name: str | None
    confidence: float | None = None
    parameters: dict[str, JsonValue] = field(default_factory=dict)
    fallback_reason: str | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Intent confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class AssistantError:
    """Structured error shape for recoverable and non-recoverable failures."""

    code: str
    message: str
    recoverable: bool = True
    details: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillRequest:
    """Typed skill invocation request produced by runtime routing."""

    skill_name: str
    transcript: Transcript
    intent: IntentResolution
    context: AssistantContext


@dataclass(frozen=True, slots=True)
class SkillResult:
    """Structured skill execution result."""

    skill_name: str
    success: bool
    spoken_response: str | None = None
    data: dict[str, JsonValue] = field(default_factory=dict)
    error: AssistantError | None = None
