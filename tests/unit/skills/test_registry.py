"""Unit tests for skill metadata validation and registry behavior."""

from __future__ import annotations

import pytest

from assistant_core.config.schema import SkillsConfig
from assistant_core.fakes import FakeSkill
from assistant_core.interfaces import SkillMetadata
from assistant_core.skills import SkillRegistry


def test_skill_metadata_accepts_extended_fields() -> None:
    metadata = SkillMetadata(
        name="time_date",
        description="Return the current time or date.",
        example_utterances=("what time is it",),
        tags=("builtin", "utility"),
        config_schema={"type": "object", "properties": {}},
        response_contract={"spoken_response": {"type": "string"}},
    )

    assert metadata.name == "time_date"
    assert metadata.config_schema["type"] == "object"
    assert "spoken_response" in metadata.response_contract


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"name": "", "description": "desc"}, "name must be a non-empty string"),
        ({"name": "skill", "description": ""}, "description must be a non-empty string"),
        (
            {"name": "skill", "description": "desc", "example_utterances": ("ok", "")},
            "example_utterances entries must be non-empty strings",
        ),
        (
            {"name": "skill", "description": "desc", "tags": ("utility", "")},
            "tags entries must be non-empty strings",
        ),
    ],
)
def test_skill_metadata_rejects_invalid_values(kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SkillMetadata(**kwargs)


def test_registry_registers_enabled_builtin_skills_from_config() -> None:
    registry = SkillRegistry(SkillsConfig(enabled_builtin_skills=("time_date",), plugin_paths=()))
    enabled_skill = FakeSkill(skill_name="time_date")
    disabled_skill = FakeSkill(skill_name="echo_debug")

    registry.register(enabled_skill)
    registry.register(disabled_skill)

    assert registry.get("time_date") is enabled_skill
    assert registry.get("echo_debug") is None
    assert registry.get("echo_debug", include_disabled=True) is disabled_skill
    assert registry.names() == ("time_date",)
    assert registry.names(include_disabled=True) == ("time_date", "echo_debug")


def test_registry_registers_plugins_enabled_by_default() -> None:
    registry = SkillRegistry(SkillsConfig(enabled_builtin_skills=(), plugin_paths=("plugins",)))
    plugin_skill = FakeSkill(skill_name="weather")

    registry.register(plugin_skill, source="plugin")

    assert registry.get("weather") is plugin_skill
    assert registry.is_enabled("weather") is True


def test_registry_rejects_duplicate_names() -> None:
    registry = SkillRegistry()
    registry.register(FakeSkill(skill_name="echo_debug"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeSkill(skill_name="echo_debug"))


def test_registry_can_enable_and_disable_registered_skills() -> None:
    registry = SkillRegistry(SkillsConfig(enabled_builtin_skills=("echo_debug",), plugin_paths=()))
    skill = FakeSkill(skill_name="echo_debug")
    registry.register(skill)

    registry.disable("echo_debug")
    assert registry.get("echo_debug") is None
    assert registry.is_enabled("echo_debug") is False

    registry.enable("echo_debug")
    assert registry.get("echo_debug") is skill
    assert registry.is_enabled("echo_debug") is True


def test_registry_register_many_preserves_order() -> None:
    registry = SkillRegistry(
        SkillsConfig(enabled_builtin_skills=("time_date", "echo_debug"), plugin_paths=())
    )
    time_skill = FakeSkill(skill_name="time_date")
    echo_skill = FakeSkill(skill_name="echo_debug")

    registry.register_many([time_skill, echo_skill])

    assert registry.names() == ("time_date", "echo_debug")
    assert registry.metadata()[0].name == "time_date"
    assert registry.all_skills() == [time_skill, echo_skill]