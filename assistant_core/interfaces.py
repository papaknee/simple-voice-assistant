"""Protocol interfaces for replaceable assistant pipeline components."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from assistant_core.models import (
    AssistantContext,
    AssistantError,
    CapturedAudio,
    IntentResolution,
    JsonValue,
    SkillRequest,
    SkillResult,
    Transcript,
)
from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType


@dataclass(frozen=True, slots=True)
class AudioDeviceInfo:
    """Audio device descriptor returned by capture/playback adapters."""

    device_id: str
    name: str
    sample_rate_hz: int
    channels: int
    input: bool = False
    output: bool = False


@dataclass(frozen=True, slots=True)
class WakeDetection:
    """Wake-word detection outcome."""

    detected: bool
    score: float | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SynthesizedAudio:
    """Synthesized speech audio payload for playback."""

    audio_bytes: bytes
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    format: str = "pcm_s16le"


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Descriptive skill metadata used by routers and registries."""

    name: str
    description: str
    version: str = "0.1.0"
    example_utterances: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    config_schema: dict[str, JsonValue] = field(default_factory=dict)
    response_contract: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("SkillMetadata name must be a non-empty string.")
        if not self.description.strip():
            raise ValueError("SkillMetadata description must be a non-empty string.")
        if any(not utterance.strip() for utterance in self.example_utterances):
            raise ValueError("SkillMetadata example_utterances entries must be non-empty strings.")
        if any(not tag.strip() for tag in self.tags):
            raise ValueError("SkillMetadata tags entries must be non-empty strings.")


RuntimeEventHandler = Callable[[RuntimeEvent], None]


@runtime_checkable
class AudioInput(Protocol):
    """Microphone capture interface."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def read_frames(self, *, max_frames: int | None = None) -> bytes: ...

    def device_info(self) -> AudioDeviceInfo: ...


@runtime_checkable
class AudioOutput(Protocol):
    """Audio playback interface for PCM output."""

    def play(self, audio: SynthesizedAudio) -> None: ...

    def stop(self) -> None: ...

    def device_info(self) -> AudioDeviceInfo: ...


@runtime_checkable
class WakeWordDetector(Protocol):
    """Wake-word engine abstraction."""

    def load(self) -> None: ...

    def reset(self) -> None: ...

    def process_frame(self, frame: bytes) -> WakeDetection: ...

    def detection_metadata(self) -> dict[str, JsonValue]: ...


@runtime_checkable
class VoiceActivityDetector(Protocol):
    """Voice activity and stop-capture policy interface."""

    def process_frame(self, frame: bytes) -> None: ...

    def is_speech(self) -> bool: ...

    def should_stop_recording(self) -> bool: ...


@runtime_checkable
class SpeechToTextEngine(Protocol):
    """Speech-to-text engine interface."""

    def transcribe(
        self,
        audio_bytes: bytes,
        audio: CapturedAudio,
        *,
        language: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> Transcript: ...


@runtime_checkable
class IntentRouter(Protocol):
    """Intent resolution interface."""

    def route(self, transcript: Transcript, context: AssistantContext) -> IntentResolution: ...


@runtime_checkable
class Skill(Protocol):
    """Skill execution interface."""

    def metadata(self) -> SkillMetadata: ...

    def can_handle(self, intent: IntentResolution) -> bool: ...

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult: ...

    def permissions(self) -> set[str]: ...


@runtime_checkable
class TextToSpeechEngine(Protocol):
    """Text-to-speech interface."""

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> SynthesizedAudio: ...


@runtime_checkable
class SoundManager(Protocol):
    """Named sound cue interface."""

    def play(self, cue_name: str) -> None: ...

    def list_available_cues(self) -> tuple[str, ...]: ...

    def validate_pack(self) -> list[AssistantError]: ...


@runtime_checkable
class RuntimeEventBus(Protocol):
    """Event publication and subscription interface."""

    def publish(self, event: RuntimeEvent) -> None: ...

    def subscribe(self, event_type: RuntimeEventType, handler: RuntimeEventHandler) -> None: ...

    def record(self, event: RuntimeEvent) -> None: ...
