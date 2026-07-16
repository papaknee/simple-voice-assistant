"""Typed configuration schema and defaults for the assistant runtime."""

from __future__ import annotations

from dataclasses import dataclass, field

from assistant_core.models import AssistantError


@dataclass(frozen=True, slots=True)
class WakeWordConfig:
    """Wake-word configuration values."""

    engine: str = "fake"
    model_path: str | None = None
    sensitivity: float = 0.5
    activation_cooldown_seconds: float = 1.0
    alternate_phrases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Audio device and stream defaults."""

    input_device: str | None = None
    output_device: str | None = None
    sample_rate_hz: int = 16000
    channels: int = 1


@dataclass(frozen=True, slots=True)
class SpeechToTextConfig:
    """Speech-to-text configuration defaults."""

    engine: str = "fake"
    model_path: str | None = None
    language: str = "en-US"
    max_utterance_seconds: float = 12.0
    silence_seconds: float = 1.0


@dataclass(frozen=True, slots=True)
class TextToSpeechConfig:
    """Text-to-speech configuration defaults."""

    engine: str = "fake"
    voice: str | None = None
    language: str = "en-US"
    speaking_rate: float = 1.0
    volume: float = 1.0


@dataclass(frozen=True, slots=True)
class SkillsConfig:
    """Built-in and plugin skill configuration."""

    enabled_builtin_skills: tuple[str, ...] = ("time_date", "echo_debug")
    plugin_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Runtime logging policy defaults."""

    level: str = "INFO"
    redact_sensitive: bool = True


@dataclass(frozen=True, slots=True)
class PrivacyConfig:
    """Transcript and audio retention controls."""

    store_transcripts: bool = False
    store_audio: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Runtime-level behavior defaults."""

    command_timeout_seconds: float = 15.0
    fallback_response: str = "I did not understand the command."


@dataclass(frozen=True, slots=True)
class AssistantConfig:
    """Top-level assistant configuration schema."""

    wake: WakeWordConfig = field(default_factory=WakeWordConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: SpeechToTextConfig = field(default_factory=SpeechToTextConfig)
    tts: TextToSpeechConfig = field(default_factory=TextToSpeechConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    def validate(self) -> list[AssistantError]:
        """Return structured validation errors for invalid configuration values."""
        errors: list[AssistantError] = []

        if not 0.0 <= self.wake.sensitivity <= 1.0:
            errors.append(
                AssistantError(
                    code="config.wake.sensitivity_range",
                    message="wake.sensitivity must be between 0.0 and 1.0.",
                    details={"value": self.wake.sensitivity},
                )
            )
        if self.wake.activation_cooldown_seconds < 0:
            errors.append(
                AssistantError(
                    code="config.wake.activation_cooldown_seconds_non_negative",
                    message="wake.activation_cooldown_seconds must be >= 0.",
                    details={"value": self.wake.activation_cooldown_seconds},
                )
            )
        if self.audio.sample_rate_hz <= 0:
            errors.append(
                AssistantError(
                    code="config.audio.sample_rate_hz_positive",
                    message="audio.sample_rate_hz must be > 0.",
                    details={"value": self.audio.sample_rate_hz},
                )
            )
        if self.audio.channels <= 0:
            errors.append(
                AssistantError(
                    code="config.audio.channels_positive",
                    message="audio.channels must be > 0.",
                    details={"value": self.audio.channels},
                )
            )
        if self.stt.max_utterance_seconds <= 0:
            errors.append(
                AssistantError(
                    code="config.stt.max_utterance_seconds_positive",
                    message="stt.max_utterance_seconds must be > 0.",
                    details={"value": self.stt.max_utterance_seconds},
                )
            )
        if self.stt.silence_seconds < 0:
            errors.append(
                AssistantError(
                    code="config.stt.silence_seconds_non_negative",
                    message="stt.silence_seconds must be >= 0.",
                    details={"value": self.stt.silence_seconds},
                )
            )
        if self.tts.speaking_rate <= 0:
            errors.append(
                AssistantError(
                    code="config.tts.speaking_rate_positive",
                    message="tts.speaking_rate must be > 0.",
                    details={"value": self.tts.speaking_rate},
                )
            )
        if not 0.0 <= self.tts.volume <= 2.0:
            errors.append(
                AssistantError(
                    code="config.tts.volume_range",
                    message="tts.volume must be between 0.0 and 2.0.",
                    details={"value": self.tts.volume},
                )
            )
        if not self.skills.enabled_builtin_skills:
            errors.append(
                AssistantError(
                    code="config.skills.enabled_builtin_skills_required",
                    message="skills.enabled_builtin_skills must include at least one skill.",
                )
            )
        if any(not path.strip() for path in self.skills.plugin_paths):
            errors.append(
                AssistantError(
                    code="config.skills.plugin_paths_non_empty",
                    message="skills.plugin_paths entries must be non-empty strings.",
                )
            )
        if self.runtime.command_timeout_seconds <= 0:
            errors.append(
                AssistantError(
                    code="config.runtime.command_timeout_seconds_positive",
                    message="runtime.command_timeout_seconds must be > 0.",
                    details={"value": self.runtime.command_timeout_seconds},
                )
            )
        return errors

    def ensure_valid(self) -> None:
        """Raise ValueError with actionable details when config is invalid."""
        errors = self.validate()
        if not errors:
            return
        message = "; ".join(f"{error.code}: {error.message}" for error in errors)
        raise ValueError(message)
