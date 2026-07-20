"""Skill protocols, metadata, registry, and execution helpers."""

from assistant_core.interfaces import Skill, SkillMetadata
from assistant_core.skills.builtins import EchoDebugSkill, TimeDateSkill, create_builtin_skills
from assistant_core.skills.executor import (
	DANGEROUS_SKILL_PERMISSIONS,
	SKILL_PERMISSIONS,
	SkillExecutionPolicy,
	SkillExecutor,
)
from assistant_core.skills.registry import RegisteredSkill, SkillRegistry

__all__ = [
	"DANGEROUS_SKILL_PERMISSIONS",
	"EchoDebugSkill",
	"RegisteredSkill",
	"SKILL_PERMISSIONS",
	"Skill",
	"SkillExecutionPolicy",
	"SkillExecutor",
	"SkillMetadata",
	"SkillRegistry",
	"TimeDateSkill",
	"create_builtin_skills",
]
