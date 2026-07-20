"""Unit tests for built-in skill implementations."""

from __future__ import annotations

from datetime import datetime, timezone

from assistant_core.models import AssistantContext, IntentResolution, SkillRequest, Transcript
from assistant_core.skills import EchoDebugSkill, SkillRegistry, TimeDateSkill, create_builtin_skills


def test_create_builtin_skills_returns_expected_registration_order() -> None:
    builtins = create_builtin_skills()

    assert tuple(skill.metadata().name for skill in builtins) == ("time_date", "echo_debug")


def test_time_date_skill_reports_time_for_get_time_intent() -> None:
    skill = TimeDateSkill(now_provider=lambda: datetime(2026, 7, 20, 15, 4, tzinfo=timezone.utc))
    context = AssistantContext(session_id="session-1")
    request = SkillRequest(
        skill_name="time_date",
        transcript=Transcript(text="what time is it"),
        intent=IntentResolution(intent_name="get_time", confidence=1.0),
        context=context,
    )

    result = skill.run(request, context)

    assert result.success is True
    assert result.spoken_response == "The time is 3:04 PM."
    assert result.data["intent_name"] == "get_time"


def test_time_date_skill_reports_date_for_get_date_intent() -> None:
    skill = TimeDateSkill(now_provider=lambda: datetime(2026, 7, 20, 15, 4, tzinfo=timezone.utc))
    context = AssistantContext(session_id="session-1")
    request = SkillRequest(
        skill_name="time_date",
        transcript=Transcript(text="what is the date"),
        intent=IntentResolution(intent_name="get_date", confidence=1.0),
        context=context,
    )

    result = skill.run(request, context)

    assert result.success is True
    assert result.spoken_response == "Today's date is July 20, 2026."
    assert result.data["intent_name"] == "get_date"


def test_echo_debug_skill_prefers_extracted_message_parameter() -> None:
    skill = EchoDebugSkill()
    context = AssistantContext(session_id="session-1")
    request = SkillRequest(
        skill_name="echo_debug",
        transcript=Transcript(text="echo hello world"),
        intent=IntentResolution(
            intent_name="echo_debug",
            confidence=1.0,
            parameters={"message": "hello world"},
        ),
        context=context,
    )

    result = skill.run(request, context)

    assert result.success is True
    assert result.spoken_response == "Echo: hello world"
    assert result.data["echoed_text"] == "hello world"


def test_echo_debug_skill_falls_back_to_full_transcript() -> None:
    skill = EchoDebugSkill()
    context = AssistantContext(session_id="session-1")
    request = SkillRequest(
        skill_name="echo_debug",
        transcript=Transcript(text="echo raw transcript"),
        intent=IntentResolution(intent_name="echo_debug", confidence=1.0),
        context=context,
    )

    result = skill.run(request, context)

    assert result.success is True
    assert result.spoken_response == "Echo: echo raw transcript"


def test_builtin_skills_register_with_registry_and_enabled_filtering() -> None:
    registry = SkillRegistry()

    registry.register_many(create_builtin_skills())

    assert registry.names() == ("time_date", "echo_debug")


def test_time_date_skill_can_handle_routed_sub_intents() -> None:
    skill = TimeDateSkill()

    assert skill.can_handle(IntentResolution(intent_name="get_time")) is True
    assert skill.can_handle(IntentResolution(intent_name="get_date")) is True
    assert skill.can_handle(IntentResolution(intent_name="time_date")) is True
    assert skill.can_handle(IntentResolution(intent_name="echo_debug")) is False