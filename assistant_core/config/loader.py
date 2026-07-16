"""Configuration loading, merging, environment overrides, and validation."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

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
from assistant_core.models import AssistantError

ENV_PREFIX = "ASSISTANT_"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2].joinpath("config").joinpath("default.toml")
)


class ConfigLoadError(ValueError):
    """Raised when configuration loading or validation fails."""

    def __init__(self, errors: tuple[AssistantError, ...]) -> None:
        self.errors = errors
        message = "; ".join(f"{error.code}: {error.message}" for error in errors)
        super().__init__(message)


def load_assistant_config(
    default_path: Path | None = None,
    user_path: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> AssistantConfig:
    """Load config from default file, optional user file, and env overrides."""
    raw_config = _default_raw_config()
    load_errors: list[AssistantError] = []

    default_config_path = default_path or DEFAULT_CONFIG_PATH
    _merge_toml_file(raw_config, default_config_path, load_errors)

    if user_path is not None:
        _merge_toml_file(raw_config, user_path, load_errors)

    _apply_env_overrides(raw_config, env if env is not None else os.environ, load_errors)

    if load_errors:
        raise ConfigLoadError(tuple(load_errors))

    parsed_config, parse_errors = _parse_assistant_config(raw_config)
    if parse_errors:
        raise ConfigLoadError(tuple(parse_errors))

    validation_errors = list(parsed_config.validate()) + _validate_paths(parsed_config)
    if validation_errors:
        raise ConfigLoadError(tuple(validation_errors))

    return parsed_config


def _default_raw_config() -> dict[str, dict[str, object]]:
    default_config = AssistantConfig()
    return {
        "wake": {
            "engine": default_config.wake.engine,
            "model_path": default_config.wake.model_path,
            "sensitivity": default_config.wake.sensitivity,
            "activation_cooldown_seconds": default_config.wake.activation_cooldown_seconds,
            "alternate_phrases": list(default_config.wake.alternate_phrases),
        },
        "audio": {
            "input_device": default_config.audio.input_device,
            "output_device": default_config.audio.output_device,
            "sample_rate_hz": default_config.audio.sample_rate_hz,
            "channels": default_config.audio.channels,
        },
        "stt": {
            "engine": default_config.stt.engine,
            "model_path": default_config.stt.model_path,
            "language": default_config.stt.language,
            "max_utterance_seconds": default_config.stt.max_utterance_seconds,
            "silence_seconds": default_config.stt.silence_seconds,
        },
        "tts": {
            "engine": default_config.tts.engine,
            "voice": default_config.tts.voice,
            "language": default_config.tts.language,
            "speaking_rate": default_config.tts.speaking_rate,
            "volume": default_config.tts.volume,
        },
        "skills": {
            "enabled_builtin_skills": list(default_config.skills.enabled_builtin_skills),
            "plugin_paths": list(default_config.skills.plugin_paths),
        },
        "logging": {
            "level": default_config.logging.level,
            "redact_sensitive": default_config.logging.redact_sensitive,
        },
        "privacy": {
            "store_transcripts": default_config.privacy.store_transcripts,
            "store_audio": default_config.privacy.store_audio,
        },
        "runtime": {
            "command_timeout_seconds": default_config.runtime.command_timeout_seconds,
            "fallback_response": default_config.runtime.fallback_response,
        },
    }


def _merge_toml_file(
    base_config: dict[str, dict[str, object]],
    config_path: Path,
    errors: list[AssistantError],
) -> None:
    if not config_path.exists():
        errors.append(
            AssistantError(
                code="config.file.not_found",
                message=f"Configuration file not found: {config_path}",
                recoverable=False,
                details={"path": str(config_path)},
            )
        )
        return

    file_data = _load_toml_mapping(config_path, errors)
    for section_name, section_value in file_data.items():
        if section_name not in base_config:
            errors.append(
                AssistantError(
                    code="config.section.unknown",
                    message=f"Unknown config section '{section_name}' in {config_path}.",
                    details={"section": section_name, "path": str(config_path)},
                )
            )
            continue
        if not isinstance(section_value, dict):
            errors.append(
                AssistantError(
                    code="config.section.invalid_type",
                    message=f"Section '{section_name}' in {config_path} must be a table/object.",
                    details={"section": section_name, "path": str(config_path)},
                )
            )
            continue
        for key, value in section_value.items():
            if key not in base_config[section_name]:
                errors.append(
                    AssistantError(
                        code="config.key.unknown",
                        message=f"Unknown key '{section_name}.{key}' in {config_path}.",
                        details={"section": section_name, "key": key, "path": str(config_path)},
                    )
                )
                continue
            base_config[section_name][key] = value


def _load_toml_mapping(config_path: Path, errors: list[AssistantError]) -> dict[str, object]:
    try:
        loaded = cast(dict[str, object], tomllib.loads(config_path.read_text(encoding="utf-8")))
    except tomllib.TOMLDecodeError as exc:
        errors.append(
            AssistantError(
                code="config.file.toml_decode_error",
                message=f"Invalid TOML in {config_path}: {exc}",
                recoverable=False,
                details={"path": str(config_path)},
            )
        )
        return {}
    except OSError as exc:
        errors.append(
            AssistantError(
                code="config.file.read_error",
                message=f"Failed to read configuration file {config_path}: {exc}",
                recoverable=False,
                details={"path": str(config_path)},
            )
        )
        return {}
    return loaded


def _apply_env_overrides(
    base_config: dict[str, dict[str, object]],
    env: Mapping[str, str],
    errors: list[AssistantError],
) -> None:
    for key, value in env.items():
        if not key.startswith(ENV_PREFIX):
            continue
        remainder = key[len(ENV_PREFIX) :]
        section_and_key = remainder.split("__", maxsplit=1)
        if len(section_and_key) != 2:
            errors.append(
                AssistantError(
                    code="config.env.key_invalid",
                    message=f"Environment override key '{key}' must be ASSISTANT_<SECTION>__<KEY>.",
                    details={"key": key},
                )
            )
            continue
        section_name = section_and_key[0].strip().lower()
        field_name = section_and_key[1].strip().lower()
        if section_name not in base_config:
            errors.append(
                AssistantError(
                    code="config.env.section_unknown",
                    message=f"Environment override section '{section_name}' is unknown.",
                    details={"key": key, "section": section_name},
                )
            )
            continue
        if field_name not in base_config[section_name]:
            errors.append(
                AssistantError(
                    code="config.env.key_unknown",
                    message=f"Environment override key '{section_name}.{field_name}' is unknown.",
                    details={"key": key, "section": section_name, "field": field_name},
                )
            )
            continue
        base_config[section_name][field_name] = value


def _parse_assistant_config(
    raw_config: dict[str, dict[str, object]],
) -> tuple[AssistantConfig, list[AssistantError]]:
    errors: list[AssistantError] = []

    wake = WakeWordConfig(
        engine=_parse_required_string(raw_config, "wake", "engine", errors),
        model_path=_parse_optional_string(raw_config, "wake", "model_path", errors),
        sensitivity=_parse_float(raw_config, "wake", "sensitivity", errors),
        activation_cooldown_seconds=_parse_float(
            raw_config, "wake", "activation_cooldown_seconds", errors
        ),
        alternate_phrases=_parse_string_tuple(raw_config, "wake", "alternate_phrases", errors),
    )
    audio = AudioConfig(
        input_device=_parse_optional_string(raw_config, "audio", "input_device", errors),
        output_device=_parse_optional_string(raw_config, "audio", "output_device", errors),
        sample_rate_hz=_parse_int(raw_config, "audio", "sample_rate_hz", errors),
        channels=_parse_int(raw_config, "audio", "channels", errors),
    )
    stt = SpeechToTextConfig(
        engine=_parse_required_string(raw_config, "stt", "engine", errors),
        model_path=_parse_optional_string(raw_config, "stt", "model_path", errors),
        language=_parse_required_string(raw_config, "stt", "language", errors),
        max_utterance_seconds=_parse_float(raw_config, "stt", "max_utterance_seconds", errors),
        silence_seconds=_parse_float(raw_config, "stt", "silence_seconds", errors),
    )
    tts = TextToSpeechConfig(
        engine=_parse_required_string(raw_config, "tts", "engine", errors),
        voice=_parse_optional_string(raw_config, "tts", "voice", errors),
        language=_parse_required_string(raw_config, "tts", "language", errors),
        speaking_rate=_parse_float(raw_config, "tts", "speaking_rate", errors),
        volume=_parse_float(raw_config, "tts", "volume", errors),
    )
    skills = SkillsConfig(
        enabled_builtin_skills=_parse_string_tuple(
            raw_config, "skills", "enabled_builtin_skills", errors
        ),
        plugin_paths=_parse_string_tuple(raw_config, "skills", "plugin_paths", errors),
    )
    logging = LoggingConfig(
        level=_parse_required_string(raw_config, "logging", "level", errors),
        redact_sensitive=_parse_bool(raw_config, "logging", "redact_sensitive", errors),
    )
    privacy = PrivacyConfig(
        store_transcripts=_parse_bool(raw_config, "privacy", "store_transcripts", errors),
        store_audio=_parse_bool(raw_config, "privacy", "store_audio", errors),
    )
    runtime = RuntimeConfig(
        command_timeout_seconds=_parse_float(
            raw_config, "runtime", "command_timeout_seconds", errors
        ),
        fallback_response=_parse_required_string(
            raw_config, "runtime", "fallback_response", errors
        ),
    )

    return (
        AssistantConfig(
            wake=wake,
            audio=audio,
            stt=stt,
            tts=tts,
            skills=skills,
            logging=logging,
            privacy=privacy,
            runtime=runtime,
        ),
        errors,
    )


def _parse_required_string(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> str:
    value = raw_config[section][key]
    if isinstance(value, str):
        return value
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be a string.",
            details={"value": repr(value)},
        )
    )
    return ""


def _parse_optional_string(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> str | None:
    value = raw_config[section][key]
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized if normalized else None
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be a string or empty.",
            details={"value": repr(value)},
        )
    )
    return None


def _parse_float(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> float:
    value = raw_config[section][key]
    if isinstance(value, bool):
        errors.append(
            AssistantError(
                code=f"config.{section}.{key}_invalid_type",
                message=f"{section}.{key} must be a float.",
                details={"value": repr(value)},
            )
        )
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            pass
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be a float.",
            details={"value": repr(value)},
        )
    )
    return 0.0


def _parse_int(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> int:
    value = raw_config[section][key]
    if isinstance(value, bool):
        errors.append(
            AssistantError(
                code=f"config.{section}.{key}_invalid_type",
                message=f"{section}.{key} must be an integer.",
                details={"value": repr(value)},
            )
        )
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be an integer.",
            details={"value": repr(value)},
        )
    )
    return 0


def _parse_bool(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> bool:
    value = raw_config[section][key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be a boolean.",
            details={"value": repr(value)},
        )
    )
    return False


def _parse_string_tuple(
    raw_config: dict[str, dict[str, object]],
    section: str,
    key: str,
    errors: list[AssistantError],
) -> tuple[str, ...]:
    value = raw_config[section][key]
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return tuple(part for part in parts if part)
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return tuple(value)
        errors.append(
            AssistantError(
                code=f"config.{section}.{key}_invalid_type",
                message=f"{section}.{key} must be an array of strings.",
                details={"value": repr(value)},
            )
        )
        return ()
    if isinstance(value, tuple):
        if all(isinstance(item, str) for item in value):
            return tuple(value)
        errors.append(
            AssistantError(
                code=f"config.{section}.{key}_invalid_type",
                message=f"{section}.{key} must be an array of strings.",
                details={"value": repr(value)},
            )
        )
        return ()
    errors.append(
        AssistantError(
            code=f"config.{section}.{key}_invalid_type",
            message=f"{section}.{key} must be an array of strings.",
            details={"value": repr(value)},
        )
    )
    return ()


def _validate_paths(config: AssistantConfig) -> list[AssistantError]:
    errors: list[AssistantError] = []
    if config.wake.model_path is not None and not Path(config.wake.model_path).exists():
        errors.append(
            AssistantError(
                code="config.wake.model_path_not_found",
                message=f"wake.model_path does not exist: {config.wake.model_path}",
                details={"path": config.wake.model_path},
            )
        )
    if config.stt.model_path is not None and not Path(config.stt.model_path).exists():
        errors.append(
            AssistantError(
                code="config.stt.model_path_not_found",
                message=f"stt.model_path does not exist: {config.stt.model_path}",
                details={"path": config.stt.model_path},
            )
        )
    for plugin_path in config.skills.plugin_paths:
        path = Path(plugin_path)
        if not path.exists():
            errors.append(
                AssistantError(
                    code="config.skills.plugin_path_not_found",
                    message=f"skills.plugin_paths entry does not exist: {plugin_path}",
                    details={"path": plugin_path},
                )
            )
        elif not path.is_dir():
            errors.append(
                AssistantError(
                    code="config.skills.plugin_path_not_directory",
                    message=f"skills.plugin_paths entry must be a directory: {plugin_path}",
                    details={"path": plugin_path},
                )
            )
    return errors
