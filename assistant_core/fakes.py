"""Fake adapter implementations for deterministic runtime and tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from assistant_core.interfaces import (
    AudioDeviceInfo,
    AudioInput,
    AudioOutput,
    IntentRouter,
    Skill,
    SkillMetadata,
    SoundManager,
    SpeechToTextEngine,
    SynthesizedAudio,
    TextToSpeechEngine,
    WakeDetection,
    WakeWordDetector,
)
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
from assistant_core.runtime.event_bus import InMemoryRuntimeEventBus
from assistant_core.stt.engine import FakeSpeechToTextEngine
from assistant_core.vad.detector import FakeVoiceActivityDetector


@dataclass(slots=True)
class FakeAudioInput(AudioInput):
    """Deterministic fake microphone input backed by in-memory frames."""

    frames: list[bytes] = field(default_factory=list)
    device: AudioDeviceInfo = field(
        default_factory=lambda: AudioDeviceInfo(
            device_id="fake-mic",
            name="Fake Microphone",
            sample_rate_hz=16000,
            channels=1,
            input=True,
        )
    )
    _started: bool = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def read_frames(self, *, max_frames: int | None = None) -> bytes:
        if not self._started:
            raise RuntimeError("FakeAudioInput must be started before reading frames.")
        if not self.frames:
            return b""
        frame = self.frames.pop(0)
        if max_frames is None:
            return frame
        return frame[:max_frames]

    def device_info(self) -> AudioDeviceInfo:
        return self.device


@dataclass(slots=True)
class FakeAudioOutput(AudioOutput):
    """Deterministic fake speaker output that records played buffers."""

    device: AudioDeviceInfo = field(
        default_factory=lambda: AudioDeviceInfo(
            device_id="fake-speaker",
            name="Fake Speaker",
            sample_rate_hz=22050,
            channels=1,
            output=True,
        )
    )
    played: list[SynthesizedAudio] = field(default_factory=list)
    _stopped: bool = False

    def play(self, audio: SynthesizedAudio) -> None:
        if self._stopped:
            raise RuntimeError("FakeAudioOutput is stopped and cannot play audio.")
        self.played.append(audio)

    def stop(self) -> None:
        self._stopped = True

    def device_info(self) -> AudioDeviceInfo:
        return self.device


@dataclass(slots=True)
class FakeWakeWordDetector(WakeWordDetector):
    """Frame-matching wake detector for deterministic tests."""

    wake_frame: bytes = b"wake"
    score: float = 1.0
    _loaded: bool = False

    def load(self) -> None:
        self._loaded = True

    def reset(self) -> None:
        self._loaded = False

    def process_frame(self, frame: bytes) -> WakeDetection:
        if not self._loaded:
            raise RuntimeError("FakeWakeWordDetector must be loaded before processing frames.")
        if frame == self.wake_frame:
            return WakeDetection(detected=True, score=self.score)
        return WakeDetection(detected=False, score=0.0)

    def detection_metadata(self) -> dict[str, JsonValue]:
        return {"engine": "fake", "wake_frame": self.wake_frame.decode("utf-8", errors="ignore")}


@dataclass(slots=True)
class FakeIntentRouter(IntentRouter):
    """Fake intent router using exact transcript text mapping."""

    routes: dict[str, IntentResolution] = field(default_factory=dict)
    fallback_reason: str = "no_route"

    def route(self, transcript: Transcript, context: AssistantContext) -> IntentResolution:
        _ = context
        fallback = IntentResolution(
            intent_name=None,
            confidence=0.0,
            fallback_reason=self.fallback_reason,
        )
        return self.routes.get(
            transcript.text,
            fallback,
        )


@dataclass(slots=True)
class FakeSkill(Skill):
    """Fake skill adapter with deterministic success response."""

    skill_name: str = "echo_debug"
    description: str = "Echoes transcript text"
    response_prefix: str = "Echo:"

    def metadata(self) -> SkillMetadata:
        return SkillMetadata(name=self.skill_name, description=self.description)

    def can_handle(self, intent: IntentResolution) -> bool:
        return intent.intent_name == self.skill_name

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult:
        _ = context
        return SkillResult(
            skill_name=self.skill_name,
            success=True,
            spoken_response=f"{self.response_prefix} {request.transcript.text}",
        )

    def permissions(self) -> set[str]:
        return {"filesystem_read"}


@dataclass(slots=True)
class FakeTextToSpeechEngine(TextToSpeechEngine):
    """Fake TTS that returns encoded input text as bytes."""

    sample_rate_hz: int = 22050
    channels: int = 1
    sample_width_bytes: int = 2

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: dict[str, JsonValue] | None = None,
    ) -> SynthesizedAudio:
        _ = (voice, options)
        return SynthesizedAudio(
            audio_bytes=text.encode("utf-8"),
            sample_rate_hz=self.sample_rate_hz,
            channels=self.channels,
            sample_width_bytes=self.sample_width_bytes,
        )


@dataclass(slots=True)
class FakeSoundManager(SoundManager):
    """Fake sound manager that records played cues."""

    available_cues: tuple[str, ...] = ("wake_detected", "listening_start", "success", "error")
    played_cues: list[str] = field(default_factory=list)

    def play(self, cue_name: str) -> None:
        if cue_name not in self.available_cues:
            raise ValueError(f"Unknown sound cue: {cue_name}")
        self.played_cues.append(cue_name)

    def list_available_cues(self) -> tuple[str, ...]:
        return self.available_cues

    def validate_pack(self) -> list[AssistantError]:
        required = {"wake_detected", "success", "error"}
        missing = sorted(required.difference(self.available_cues))
        if not missing:
            return []
        missing_values: list[JsonValue] = list(missing)
        return [
            AssistantError(
                code="missing_sound_cues",
                message="Sound pack is missing required cues.",
                details={"missing": missing_values},
            )
        ]


__all__ = [
    "FakeAudioInput",
    "FakeAudioOutput",
    "FakeIntentRouter",
    "FakeSkill",
    "FakeSoundManager",
    "FakeSpeechToTextEngine",
    "FakeTextToSpeechEngine",
    "FakeVoiceActivityDetector",
    "FakeWakeWordDetector",
    "InMemoryRuntimeEventBus",
]
