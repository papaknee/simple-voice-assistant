"""Unit tests for the rule-based intent router."""

import pytest

from assistant_core.intent.router import IntentRule, RuleBasedIntentRouter
from assistant_core.interfaces import SkillMetadata
from assistant_core.models import AssistantContext, Transcript


@pytest.fixture
def basic_rules() -> list[IntentRule]:
    """Create basic intent rules for testing."""
    return [
        IntentRule(
            intent_name="get_time",
            pattern=r"(?:what\s+(?:is\s+)?the\s+time|what\s+time\s+is\s+it)",
            confidence=1.0,
        ),
        IntentRule(
            intent_name="get_date",
            pattern=r"(?:what\s+(?:is\s+)?the\s+date|what\s+date\s+is\s+it)",
            confidence=1.0,
        ),
        IntentRule(
            intent_name="echo_debug",
            pattern=r"echo\s+(?P<message>.+)",
            confidence=1.0,
        ),
    ]


@pytest.fixture
def router(basic_rules: list[IntentRule]) -> RuleBasedIntentRouter:
    """Create a router with basic rules."""
    return RuleBasedIntentRouter(rules=basic_rules)


class TestRuleBasedIntentRouter:
    """Test suite for RuleBasedIntentRouter."""

    def test_exact_match(self, router: RuleBasedIntentRouter) -> None:
        """Test exact pattern matching."""
        transcript = Transcript(text="what time is it")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name == "get_time"
        assert result.confidence == 1.0
        assert result.fallback_reason is None

    def test_case_insensitive_match(self, router: RuleBasedIntentRouter) -> None:
        """Test case-insensitive matching."""
        transcript = Transcript(text="WHAT TIME IS IT")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name == "get_time"

    def test_case_sensitive_match(self) -> None:
        """Test case-sensitive matching."""
        rules = [
            IntentRule(
                intent_name="test_case",
                pattern="Test",
                confidence=1.0,
            )
        ]
        router = RuleBasedIntentRouter(rules=rules, case_sensitive=True)
        context = AssistantContext(session_id="test-session")

        # Should not match lowercase
        result = router.route(Transcript(text="test"), context)
        assert result.intent_name is None

        # Should match exact case
        result = router.route(Transcript(text="Test"), context)
        assert result.intent_name == "test_case"

    def test_whitespace_normalization(self, router: RuleBasedIntentRouter) -> None:
        """Test whitespace normalization."""
        transcript = Transcript(text="what   is  the   time")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name == "get_time"

    def test_whitespace_no_normalization(self) -> None:
        """Test that whitespace normalization can be disabled."""
        rules = [
            IntentRule(
                intent_name="test",
                pattern="a  b",  # Expects double space
                confidence=1.0,
            )
        ]
        router = RuleBasedIntentRouter(rules=rules, normalize_whitespace=False)
        context = AssistantContext(session_id="test-session")

        # Should match with double space
        result = router.route(Transcript(text="a  b"), context)
        assert result.intent_name == "test"

        # Should not match with single space
        result = router.route(Transcript(text="a b"), context)
        assert result.intent_name is None

    def test_parameter_extraction(self, router: RuleBasedIntentRouter) -> None:
        """Test extracting parameters from matched text."""
        transcript = Transcript(text="echo hello world")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name == "echo_debug"
        assert result.parameters["message"] == "hello world"

    def test_no_match_fallback(self, router: RuleBasedIntentRouter) -> None:
        """Test fallback when no rule matches."""
        transcript = Transcript(text="something completely different")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name is None
        assert result.confidence == 0.0
        assert result.fallback_reason == "no_matching_rule"

    def test_first_matching_rule_wins(self) -> None:
        """Test that the first matching rule wins when multiple match."""
        rules = [
            IntentRule(
                intent_name="first",
                pattern="test.*",
                confidence=0.9,
            ),
            IntentRule(
                intent_name="second",
                pattern="test",
                confidence=0.8,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="test"), context)

        assert result.intent_name == "first"
        assert result.confidence == 0.9

    def test_partial_pattern_match(self, router: RuleBasedIntentRouter) -> None:
        """Test that patterns can match within text (not just full match)."""
        transcript = Transcript(text="hey, what time is it right now?")
        context = AssistantContext(session_id="test-session")

        result = router.route(transcript, context)

        assert result.intent_name == "get_time"

    def test_update_rules(self, router: RuleBasedIntentRouter) -> None:
        """Test updating rules dynamically."""
        new_rules = [
            IntentRule(
                intent_name="new_intent",
                pattern="new pattern",
                confidence=1.0,
            )
        ]

        router.update_rules(new_rules)

        context = AssistantContext(session_id="test-session")
        result = router.route(Transcript(text="new pattern"), context)
        assert result.intent_name == "new_intent"

        # Old rules should not match
        result = router.route(Transcript(text="what time is it"), context)
        assert result.intent_name is None

    def test_add_rules_from_skills(self, router: RuleBasedIntentRouter) -> None:
        """Test adding rules from skill metadata."""
        skills = [
            (
                SkillMetadata(
                    name="weather",
                    description="Get weather information",
                    example_utterances=("what is the weather", "weather today", "how hot is it"),
                ),
                "get_weather",
            ),
        ]

        router.add_rules_from_skills(skills)

        context = AssistantContext(session_id="test-session")

        # Should match first example
        result = router.route(Transcript(text="what is the weather"), context)
        assert result.intent_name == "get_weather"

        # Should match second example
        result = router.route(Transcript(text="weather today"), context)
        assert result.intent_name == "get_weather"

        # Original rules should still work
        result = router.route(Transcript(text="what time is it"), context)
        assert result.intent_name == "get_time"

    def test_add_rules_from_skills_empty_utterances(self, router: RuleBasedIntentRouter) -> None:
        """Test that skills without example utterances are skipped."""
        initial_rule_count = len(router.rules)

        skills = [
            (
                SkillMetadata(
                    name="silent_skill",
                    description="No examples",
                    example_utterances=(),
                ),
                "silent_intent",
            ),
        ]

        router.add_rules_from_skills(skills)

        # Rules should not have been added
        assert len(router.rules) == initial_rule_count

    def test_enable_intent(self, router: RuleBasedIntentRouter) -> None:
        """Test enabling/disabling intents."""
        context = AssistantContext(session_id="test-session")

        # Initially, all intents should be enabled
        result = router.route(Transcript(text="what time is it"), context)
        assert result.intent_name == "get_time"

        # Disable the intent
        router.disable_intent("get_time")
        result = router.route(Transcript(text="what time is it"), context)
        assert result.intent_name is None

        # Re-enable the intent
        router.enable_intent("get_time")
        result = router.route(Transcript(text="what time is it"), context)
        assert result.intent_name == "get_time"

    def test_disable_all_intents(self, router: RuleBasedIntentRouter) -> None:
        """Test that disabling all intents results in fallback."""
        router.disable_intent("get_time")
        router.disable_intent("get_date")
        router.disable_intent("echo_debug")

        context = AssistantContext(session_id="test-session")
        result = router.route(Transcript(text="what time is it"), context)

        assert result.intent_name is None
        assert result.fallback_reason == "no_enabled_intents"

    def test_confidence_scores(self, router: RuleBasedIntentRouter) -> None:
        """Test that confidence scores are preserved from rules."""
        rules = [
            IntentRule(
                intent_name="high_confidence",
                pattern=r"\bcertain\b",
                confidence=0.95,
            ),
            IntentRule(
                intent_name="low_confidence",
                pattern=r"\buncertain\b",
                confidence=0.5,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="certain"), context)
        assert result.confidence == 0.95

        result = router.route(Transcript(text="uncertain"), context)
        assert result.confidence == 0.5

    def test_multiple_parameter_extraction(self) -> None:
        """Test extracting multiple parameters from a single rule."""
        rules = [
            IntentRule(
                intent_name="set_value",
                pattern=r"set\s+(?P<key>\w+)\s+to\s+(?P<value>[\d.]+)",
                confidence=1.0,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="set volume to 50"), context)

        assert result.intent_name == "set_value"
        assert result.parameters["key"] == "volume"
        assert result.parameters["value"] == "50"

    def test_invalid_regex_raises_error(self) -> None:
        """Test that invalid regex patterns raise ValueError."""
        rules = [
            IntentRule(
                intent_name="bad",
                pattern="(?P<invalid",  # Invalid regex
                confidence=1.0,
            )
        ]

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            RuleBasedIntentRouter(rules=rules)

    def test_empty_rules(self) -> None:
        """Test router with no rules."""
        router = RuleBasedIntentRouter(rules=[])
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="anything"), context)

        assert result.intent_name is None
        assert result.fallback_reason == "no_matching_rule"

    def test_special_characters_in_parameters(self) -> None:
        """Test extracting parameters with special characters."""
        rules = [
            IntentRule(
                intent_name="search",
                pattern=r"search\s+for\s+(?P<query>.*)",
                confidence=1.0,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="search for hello@world.com"), context)

        assert result.intent_name == "search"
        assert result.parameters["query"] == "hello@world.com"

    def test_rule_order_matters(self) -> None:
        """Test that rule order affects matching priority."""
        rules_a = [
            IntentRule(
                intent_name="specific",
                pattern=r"hello world",
                confidence=1.0,
            ),
            IntentRule(
                intent_name="general",
                pattern=r"hello.*",
                confidence=0.8,
            ),
        ]
        rules_b = [
            IntentRule(
                intent_name="general",
                pattern=r"hello.*",
                confidence=0.8,
            ),
            IntentRule(
                intent_name="specific",
                pattern=r"hello world",
                confidence=1.0,
            ),
        ]

        router_a = RuleBasedIntentRouter(rules=rules_a)
        router_b = RuleBasedIntentRouter(rules=rules_b)
        context = AssistantContext(session_id="test-session")

        result_a = router_a.route(Transcript(text="hello world"), context)
        result_b = router_b.route(Transcript(text="hello world"), context)

        # Same input, different rule order should give different results
        assert result_a.intent_name == "specific"
        assert result_b.intent_name == "general"

    def test_enabled_intents_subset(self) -> None:
        """Test enabling only a subset of intents."""
        rules = [
            IntentRule(
                intent_name="intent_a",
                pattern="pattern_a",
                confidence=1.0,
            ),
            IntentRule(
                intent_name="intent_b",
                pattern="pattern_b",
                confidence=1.0,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules, enabled_intents={"intent_a"})
        context = AssistantContext(session_id="test-session")

        # intent_a should match
        result = router.route(Transcript(text="pattern_a"), context)
        assert result.intent_name == "intent_a"

        # intent_b should not match
        result = router.route(Transcript(text="pattern_b"), context)
        assert result.intent_name is None

    def test_alias_pattern_match(self) -> None:
        """Test that aliases can independently match an intent rule."""
        rules = [
            IntentRule(
                intent_name="get_time",
                pattern=r"what time is it",
                aliases=(r"tell me the time", r"current time"),
                confidence=0.9,
            )
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="tell me the time"), context)
        assert result.intent_name == "get_time"
        assert result.confidence == 0.9

    def test_low_confidence_fallback(self) -> None:
        """Test low-confidence fallback when score is below threshold."""
        rules = [
            IntentRule(
                intent_name="weak_match",
                pattern=r"do something",
                confidence=0.5,
            )
        ]
        router = RuleBasedIntentRouter(rules=rules, minimum_confidence=0.4)
        context = AssistantContext(session_id="test-session")

        # 0.5 * 0.5 = 0.25 which is below threshold
        result = router.route(Transcript(text="do something", confidence=0.5), context)

        assert result.intent_name is None
        assert result.fallback_reason == "low_confidence"
        assert result.confidence == pytest.approx(0.25)

    def test_ambiguous_intent_fallback(self) -> None:
        """Test ambiguity fallback when top matches are too close."""
        rules = [
            IntentRule(
                intent_name="set_timer",
                pattern=r"set",
                confidence=0.9,
            ),
            IntentRule(
                intent_name="set_alarm",
                pattern=r"set",
                confidence=0.86,
            ),
        ]
        router = RuleBasedIntentRouter(rules=rules, ambiguity_margin=0.05)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="set for five minutes"), context)

        assert result.intent_name is None
        assert result.fallback_reason == "ambiguous_intent"
        assert result.parameters["primary_candidate"] == "set_timer"
        assert result.parameters["other_candidates"] == ["set_alarm"]

    def test_empty_transcript_fallback(self, router: RuleBasedIntentRouter) -> None:
        """Test empty transcript fallback."""
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="   \t  \n"), context)

        assert result.intent_name is None
        assert result.fallback_reason == "empty_transcript"
        assert result.confidence == 0.0

    def test_transcript_confidence_scales_intent_confidence(self) -> None:
        """Test transcript confidence contributes to final routing confidence."""
        rules = [
            IntentRule(
                intent_name="get_time",
                pattern=r"what time is it",
                confidence=0.8,
            )
        ]
        router = RuleBasedIntentRouter(rules=rules)
        context = AssistantContext(session_id="test-session")

        result = router.route(Transcript(text="what time is it", confidence=0.5), context)

        assert result.intent_name == "get_time"
        assert result.confidence == pytest.approx(0.4)
