"""Skill registry helpers for built-in and plugin-provided skills."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from assistant_core.config.schema import SkillsConfig
from assistant_core.interfaces import Skill, SkillMetadata


@dataclass(frozen=True, slots=True)
class RegisteredSkill:
    """Registered skill entry with source and enabled state."""

    skill: Skill
    metadata: SkillMetadata
    source: str = "builtin"
    enabled: bool = True


class SkillRegistry:
    """Deterministic in-memory registry for skill discovery and selection."""

    def __init__(self, config: SkillsConfig | None = None) -> None:
        self._config = config or SkillsConfig()
        self._entries: dict[str, RegisteredSkill] = {}

    def register(self, skill: Skill, *, source: str = "builtin", enabled: bool | None = None) -> None:
        """Register a skill by its metadata name."""
        metadata = skill.metadata()
        if metadata.name in self._entries:
            raise ValueError(f"Skill '{metadata.name}' is already registered.")

        entry_enabled = self._is_enabled_by_default(metadata.name, source) if enabled is None else enabled
        self._entries[metadata.name] = RegisteredSkill(
            skill=skill,
            metadata=metadata,
            source=source,
            enabled=entry_enabled,
        )

    def register_many(self, skills: Iterable[Skill], *, source: str = "builtin") -> None:
        """Register multiple skills from the same source."""
        for skill in skills:
            self.register(skill, source=source)

    def get(self, skill_name: str, *, include_disabled: bool = False) -> Skill | None:
        """Return a registered skill by name."""
        entry = self._entries.get(skill_name)
        if entry is None:
            return None
        if not include_disabled and not entry.enabled:
            return None
        return entry.skill

    def metadata(self, *, include_disabled: bool = False) -> list[SkillMetadata]:
        """Return skill metadata in registration order."""
        return [
            entry.metadata
            for entry in self._entries.values()
            if include_disabled or entry.enabled
        ]

    def entries(self, *, include_disabled: bool = False) -> list[RegisteredSkill]:
        """Return registered skill entries in registration order."""
        return [
            entry
            for entry in self._entries.values()
            if include_disabled or entry.enabled
        ]

    def all_skills(self, *, include_disabled: bool = False) -> list[Skill]:
        """Return registered skill instances in registration order."""
        return [entry.skill for entry in self.entries(include_disabled=include_disabled)]

    def enable(self, skill_name: str) -> None:
        """Enable a previously registered skill."""
        self._entries[skill_name] = self._replace_enabled(skill_name, True)

    def disable(self, skill_name: str) -> None:
        """Disable a previously registered skill."""
        self._entries[skill_name] = self._replace_enabled(skill_name, False)

    def is_enabled(self, skill_name: str) -> bool:
        """Return whether a registered skill is currently enabled."""
        entry = self._entries.get(skill_name)
        if entry is None:
            return False
        return entry.enabled

    def names(self, *, include_disabled: bool = False) -> tuple[str, ...]:
        """Return registered skill names in registration order."""
        return tuple(entry.metadata.name for entry in self.entries(include_disabled=include_disabled))

    def _replace_enabled(self, skill_name: str, enabled: bool) -> RegisteredSkill:
        entry = self._entries.get(skill_name)
        if entry is None:
            raise KeyError(f"Skill '{skill_name}' is not registered.")
        return RegisteredSkill(
            skill=entry.skill,
            metadata=entry.metadata,
            source=entry.source,
            enabled=enabled,
        )

    def _is_enabled_by_default(self, skill_name: str, source: str) -> bool:
        if source == "builtin":
            return skill_name in self._config.enabled_builtin_skills
        return True