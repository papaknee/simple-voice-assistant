"""Tests for typed configuration schema defaults and validation."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from assistant_core.config.schema import (
    AssistantConfig,
    AudioConfig,
    RuntimeConfig,
    WakeWordConfig,
)


def test_assistant_config_defaults_match_mvp_decisions() -> None:
    config = AssistantConfig()
    assert config.skills.enabled_builtin_skills == ("time_date", "echo_debug")
    assert config.privacy.store_transcripts is False
    assert config.privacy.store_audio is False


def test_assistant_config_validate_returns_actionable_errors() -> None:
    config = AssistantConfig(
        wake=WakeWordConfig(sensitivity=1.5),
        audio=AudioConfig(sample_rate_hz=0, channels=0),
        runtime=RuntimeConfig(command_timeout_seconds=0),
    )
    errors = config.validate()
    codes = {error.code for error in errors}
    assert "config.wake.sensitivity_range" in codes
    assert "config.audio.sample_rate_hz_positive" in codes
    assert "config.audio.channels_positive" in codes
    assert "config.runtime.command_timeout_seconds_positive" in codes


def test_assistant_config_ensure_valid_raises_with_error_codes() -> None:
    config = AssistantConfig(wake=WakeWordConfig(sensitivity=-0.1))
    with pytest.raises(ValueError, match="config.wake.sensitivity_range"):
        config.ensure_valid()


def test_default_toml_is_parseable_and_contains_required_sections() -> None:
    default_path = Path(__file__).resolve().parents[3].joinpath("config").joinpath("default.toml")
    data = tomllib.loads(default_path.read_text(encoding="utf-8"))
    for required in ("wake", "audio", "stt", "tts", "skills", "logging", "privacy", "runtime"):
        assert required in data


def test_sample_toml_files_are_parseable_and_contain_required_sections() -> None:
    config_dir = Path(__file__).resolve().parents[3].joinpath("config")
    sample_names = (
        "development.toml",
        "reference-raspberry-pi4.toml",
        "reference-mini-pc.toml",
    )
    for file_name in sample_names:
        data = tomllib.loads(config_dir.joinpath(file_name).read_text(encoding="utf-8"))
        for required in ("wake", "audio", "stt", "tts", "skills", "logging", "privacy", "runtime"):
            assert required in data
