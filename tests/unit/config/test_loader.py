"""Tests for config file loading, environment overrides, and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from assistant_core.config.loader import ConfigLoadError, load_assistant_config


def test_load_assistant_config_merges_default_and_user_files(tmp_path: Path) -> None:
    default_path = _write_toml(
        tmp_path,
        "default.toml",
        """
        [audio]
        sample_rate_hz = 16000
        channels = 1
        """,
    )
    user_path = _write_toml(
        tmp_path,
        "user.toml",
        """
        [audio]
        sample_rate_hz = 22050
        """,
    )

    config = load_assistant_config(default_path=default_path, user_path=user_path, env={})

    assert config.audio.sample_rate_hz == 22050
    assert config.audio.channels == 1


def test_load_assistant_config_uses_schema_defaults_when_fields_are_missing(tmp_path: Path) -> None:
    default_path = _write_toml(tmp_path, "default.toml", "")

    config = load_assistant_config(default_path=default_path, env={})

    assert config.wake.engine == "fake"
    assert config.audio.sample_rate_hz == 16000


def test_load_assistant_config_raises_for_invalid_types(tmp_path: Path) -> None:
    default_path = _write_toml(
        tmp_path,
        "default.toml",
        """
        [audio]
        sample_rate_hz = "fast"
        """,
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_assistant_config(default_path=default_path, env={})

    codes = {error.code for error in exc_info.value.errors}
    assert "config.audio.sample_rate_hz_invalid_type" in codes


def test_load_assistant_config_raises_for_invalid_model_path(tmp_path: Path) -> None:
    default_path = _write_toml(
        tmp_path,
        "default.toml",
        """
        [wake]
        model_path = "C:\\\\does-not-exist\\\\wake_model.onnx"
        """,
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_assistant_config(default_path=default_path, env={})

    codes = {error.code for error in exc_info.value.errors}
    assert "config.wake.model_path_not_found" in codes


def test_load_assistant_config_raises_when_builtin_skills_disabled(tmp_path: Path) -> None:
    default_path = _write_toml(
        tmp_path,
        "default.toml",
        """
        [skills]
        enabled_builtin_skills = []
        """,
    )

    with pytest.raises(ConfigLoadError) as exc_info:
        load_assistant_config(default_path=default_path, env={})

    codes = {error.code for error in exc_info.value.errors}
    assert "config.skills.enabled_builtin_skills_required" in codes


def test_load_assistant_config_env_override_precedence(tmp_path: Path) -> None:
    default_path = _write_toml(
        tmp_path,
        "default.toml",
        """
        [audio]
        sample_rate_hz = 16000
        """,
    )
    user_path = _write_toml(
        tmp_path,
        "user.toml",
        """
        [audio]
        sample_rate_hz = 22050
        """,
    )

    config = load_assistant_config(
        default_path=default_path,
        user_path=user_path,
        env={"ASSISTANT_AUDIO__SAMPLE_RATE_HZ": "44100"},
    )

    assert config.audio.sample_rate_hz == 44100


def test_load_assistant_config_supports_all_sample_configs() -> None:
    config_dir = Path(__file__).resolve().parents[3].joinpath("config")
    sample_names = (
        "default.toml",
        "development.toml",
        "reference-raspberry-pi4.toml",
        "reference-mini-pc.toml",
    )
    for file_name in sample_names:
        loaded = load_assistant_config(default_path=config_dir.joinpath(file_name), env={})
        assert loaded.skills.enabled_builtin_skills


def _write_toml(base_path: Path, file_name: str, content: str) -> Path:
    config_path = base_path.joinpath(file_name)
    config_path.write_text(content, encoding="utf-8")
    return config_path
