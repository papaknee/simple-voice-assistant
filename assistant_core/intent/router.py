"""Rule-based intent router with pattern matching, aliases, and parameter extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Pattern

from assistant_core.interfaces import IntentRouter, SkillMetadata
from assistant_core.models import (
    AssistantContext,
    IntentResolution,
    JsonValue,
    Transcript,
)


@dataclass(frozen=True, slots=True)
class IntentRule:
    """A single intent matching rule."""

    intent_name: str
    """The intent name to route to."""

    pattern: str
    """Regex pattern to match against normalized transcript text."""

    aliases: tuple[str, ...] = ()
    """Alternative patterns for the same intent."""

    parameters: dict[str, str] = field(default_factory=dict)
    """Named capture groups to extract parameters from the transcript."""

    confidence: float = 1.0
    """Confidence level for this rule (0.0 to 1.0)."""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("IntentRule confidence must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class _CompiledIntentRule:
    """Compiled intent rule and metadata used during routing."""

    intent_name: str
    patterns: tuple[Pattern[str], ...]
    parameter_names: tuple[str, ...]
    confidence: float


class RuleBasedIntentRouter(IntentRouter):
    """Deterministic intent router using pattern matching and aliases."""

    def __init__(
        self,
        rules: list[IntentRule] | None = None,
        *,
        case_sensitive: bool = False,
        normalize_whitespace: bool = True,
        enabled_intents: set[str] | None = None,
        minimum_confidence: float = 0.35,
        ambiguity_margin: float = 0.05,
    ) -> None:
        """
        Initialize the rule-based intent router.

        Args:
            rules: List of intent rules to match against.
            case_sensitive: Whether to perform case-sensitive matching.
            normalize_whitespace: Whether to collapse multiple spaces to single space.
            enabled_intents: Optional set of enabled intent names; if provided,
                            only rules with intent_name in this set will match.
        """
        self.rules = rules or []
        self.case_sensitive = case_sensitive
        self.normalize_whitespace = normalize_whitespace
        self.enabled_intents = enabled_intents
        self.minimum_confidence = minimum_confidence
        self.ambiguity_margin = ambiguity_margin

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0.0 and 1.0.")
        if self.ambiguity_margin < 0.0:
            raise ValueError("ambiguity_margin must be zero or positive.")

        # Pre-compile patterns for efficiency
        self._compiled_rules: list[_CompiledIntentRule] = self._compile_rules(self.rules)

    def route(self, transcript: Transcript, context: AssistantContext) -> IntentResolution:
        """
        Route a transcript to an intent.

        Args:
            transcript: The STT output to route.
            context: The per-turn runtime context (unused but required by protocol).

        Returns:
            IntentResolution with the matched intent, parameters, and confidence,
            or a fallback resolution if no rule matched.
        """
        _ = context

        # Normalize the transcript text
        text = self._normalize_text(transcript.text)

        if text == "":
            return IntentResolution(
                intent_name=None,
                confidence=0.0,
                fallback_reason="empty_transcript",
            )

        if not self._compiled_rules:
            return IntentResolution(
                intent_name=None,
                confidence=0.0,
                fallback_reason="no_matching_rule",
            )

        active_rules = [rule for rule in self._compiled_rules if self._is_intent_enabled(rule.intent_name)]
        if not active_rules:
            return IntentResolution(
                intent_name=None,
                confidence=0.0,
                fallback_reason="no_enabled_intents",
            )

        matches: list[tuple[_CompiledIntentRule, re.Match[str], float]] = []
        for compiled_rule in active_rules:
            for compiled_pattern in compiled_rule.patterns:
                match = compiled_pattern.search(text)
                if match is None:
                    continue
                score = self._compute_confidence(
                    base_confidence=compiled_rule.confidence,
                    transcript_confidence=transcript.confidence,
                )
                matches.append((compiled_rule, match, score))
                break

        if not matches:
            return IntentResolution(
                intent_name=None,
                confidence=0.0,
                fallback_reason="no_matching_rule",
            )

        primary_rule, primary_match, primary_score = matches[0]

        if primary_score < self.minimum_confidence:
            return IntentResolution(
                intent_name=None,
                confidence=primary_score,
                fallback_reason="low_confidence",
            )

        ambiguous_candidates = [
            rule.intent_name
            for rule, _, score in matches[1:]
            if rule.intent_name != primary_rule.intent_name
            and abs(primary_score - score) < self.ambiguity_margin
        ]
        if ambiguous_candidates:
            return IntentResolution(
                intent_name=None,
                confidence=primary_score,
                parameters={
                    "primary_candidate": primary_rule.intent_name,
                    "other_candidates": ambiguous_candidates,
                },
                fallback_reason="ambiguous_intent",
            )

        extracted = self._extract_parameters(primary_match, primary_rule.parameter_names)
        return IntentResolution(
            intent_name=primary_rule.intent_name,
            confidence=primary_score,
            parameters=extracted,
        )

    def update_rules(self, rules: list[IntentRule]) -> None:
        """Update the router with a new set of rules."""
        self.rules = rules
        self._compiled_rules = self._compile_rules(self.rules)

    def add_rules_from_skills(self, skills: list[tuple[SkillMetadata, str]]) -> None:
        """
        Add rules from skill metadata.

        Args:
            skills: List of (SkillMetadata, intent_name) pairs.
                   Example utterances from metadata are used to create rules.
        """
        new_rules = []
        for metadata, intent_name in skills:
            if not metadata.example_utterances:
                continue

            # Create a rule that matches any of the example utterances
            # Escape special regex chars and join with OR
            escaped_examples = [re.escape(utt) for utt in metadata.example_utterances]
            pattern = "|".join(f"(?:{exp})" for exp in escaped_examples)

            rule = IntentRule(
                intent_name=intent_name,
                pattern=pattern,
                confidence=1.0,
            )
            new_rules.append(rule)

        self.update_rules(self.rules + new_rules)

    def enable_intent(self, intent_name: str) -> None:
        """Enable an intent for routing."""
        if self.enabled_intents is None:
            self.enabled_intents = {rule.intent_name for rule in self.rules}
        self.enabled_intents.add(intent_name)

    def disable_intent(self, intent_name: str) -> None:
        """Disable an intent from routing."""
        if self.enabled_intents is None:
            self.enabled_intents = {rule.intent_name for rule in self.rules}
        self.enabled_intents.discard(intent_name)

    def _normalize_text(self, text: str) -> str:
        """Normalize transcript text for matching."""
        if not self.case_sensitive:
            text = text.lower()
        if self.normalize_whitespace:
            text = " ".join(text.split())
        return text.strip()

    def _extract_parameters(self, match: re.Match[str], parameter_names: tuple[str, ...]) -> dict[str, JsonValue]:
        """Extract named capture groups from a regex match."""
        groups = match.groupdict()
        if not parameter_names:
            return {name: value for name, value in groups.items() if value is not None}
        return {
            name: value
            for name in parameter_names
            if (value := groups.get(name)) is not None
        }

    def _compute_confidence(self, *, base_confidence: float, transcript_confidence: float | None) -> float:
        """Compute final routing confidence from rule and transcript confidences."""
        if transcript_confidence is None:
            return base_confidence
        return max(0.0, min(1.0, base_confidence * transcript_confidence))

    def _is_intent_enabled(self, intent_name: str) -> bool:
        """Determine whether an intent is enabled for routing."""
        if self.enabled_intents is None:
            return True
        return intent_name in self.enabled_intents

    def _compile_rules(self, rules: list[IntentRule]) -> list[_CompiledIntentRule]:
        """Compile routing rules and aliases into regex patterns."""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        compiled_rules: list[_CompiledIntentRule] = []
        for idx, rule in enumerate(rules):
            raw_patterns = (rule.pattern, *rule.aliases)
            compiled_patterns: list[Pattern[str]] = []
            for raw_pattern in raw_patterns:
                try:
                    compiled_patterns.append(re.compile(raw_pattern, flags))
                except re.error as error:
                    raise ValueError(
                        f"Invalid regex pattern in rule {idx} ({rule.intent_name}): {error}"
                    ) from error

            parameter_names = tuple(rule.parameters) if rule.parameters else ()
            compiled_rules.append(
                _CompiledIntentRule(
                    intent_name=rule.intent_name,
                    patterns=tuple(compiled_patterns),
                    parameter_names=parameter_names,
                    confidence=rule.confidence,
                )
            )

        return compiled_rules
