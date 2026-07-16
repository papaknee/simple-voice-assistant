"""Typed configuration schema exports."""

from assistant_core.config.loader import (
    DEFAULT_CONFIG_PATH,
    ENV_PREFIX,
    ConfigLoadError,
    load_assistant_config,
)
from assistant_core.config.schema import (
    AssistantConfig,
    AudioConfig,
    LoggingConfig,
    PrivacyConfig,
    RuntimeConfig,
    SkillsConfig,
    SpeechToTextConfig,
    TextToSpeechConfig,
    WakeWordConfig,
)

__all__ = [
    "ConfigLoadError",
    "DEFAULT_CONFIG_PATH",
    "ENV_PREFIX",
    "load_assistant_config",
    "AssistantConfig",
    "AudioConfig",
    "LoggingConfig",
    "PrivacyConfig",
    "RuntimeConfig",
    "SkillsConfig",
    "SpeechToTextConfig",
    "TextToSpeechConfig",
    "WakeWordConfig",
]
