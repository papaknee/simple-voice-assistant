"""Built-in skill implementations used by the local MVP runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from assistant_core.interfaces import Skill, SkillMetadata
from assistant_core.models import AssistantContext, IntentResolution, SkillRequest, SkillResult


def _now_local() -> datetime:
    return datetime.now().astimezone()


@dataclass(slots=True)
class TimeDateSkill(Skill):
    """Built-in skill that reports the local time or date."""

    now_provider: Callable[[], datetime] = field(default=_now_local)

    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="time_date",
            description="Reports the current local time or date.",
            example_utterances=(
                "what time is it",
                "what is the date",
            ),
            tags=("builtin", "utility", "time"),
            response_contract={"spoken_response": {"type": "string"}},
        )

    def can_handle(self, intent: IntentResolution) -> bool:
        return intent.intent_name in {"time_date", "get_time", "get_date"}

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult:
        _ = context
        now = self.now_provider()
        if request.intent.intent_name == "get_date":
            response = f"Today's date is {now.strftime('%B %d, %Y')}."
        else:
            response = f"The time is {now.strftime('%I:%M %p').lstrip('0')}."
        return SkillResult(
            skill_name=self.metadata().name,
            success=True,
            spoken_response=response,
            data={
                "intent_name": request.intent.intent_name or self.metadata().name,
                "iso_timestamp": now.isoformat(),
            },
        )

    def permissions(self) -> set[str]:
        return set()


@dataclass(slots=True)
class EchoDebugSkill(Skill):
    """Built-in skill that echoes routed transcript or extracted parameters."""

    response_prefix: str = "Echo:"

    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="echo_debug",
            description="Echoes the recognized command text for debugging.",
            example_utterances=(
                "echo hello world",
                "echo testing one two three",
            ),
            tags=("builtin", "debug"),
            response_contract={
                "spoken_response": {"type": "string"},
                "data": {"type": "object"},
            },
        )

    def can_handle(self, intent: IntentResolution) -> bool:
        return intent.intent_name == self.metadata().name

    def run(self, request: SkillRequest, context: AssistantContext) -> SkillResult:
        _ = context
        message = request.intent.parameters.get("message")
        if not isinstance(message, str) or not message.strip():
            message = request.transcript.text

        spoken_response = f"{self.response_prefix} {message.strip()}"
        return SkillResult(
            skill_name=self.metadata().name,
            success=True,
            spoken_response=spoken_response,
            data={"echoed_text": message.strip()},
        )

    def permissions(self) -> set[str]:
        return set()


def create_builtin_skills() -> tuple[Skill, ...]:
    """Return the default built-in skill set in stable registration order."""
    return (TimeDateSkill(), EchoDebugSkill())