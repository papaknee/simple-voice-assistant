"""Unit tests for the CachingTextToSpeechEngine LRU wrapper."""

from __future__ import annotations

import pytest

from assistant_core.config.schema import TextToSpeechConfig
from assistant_core.interfaces import SynthesizedAudio, TextToSpeechEngine
from assistant_core.tts import CachingTextToSpeechEngine, FakeTextToSpeechEngine, create_tts_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache(max_entries: int = 8) -> tuple[CachingTextToSpeechEngine, FakeTextToSpeechEngine]:
    inner = FakeTextToSpeechEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=max_entries)
    return cache, inner


class _CountingEngine(TextToSpeechEngine):
    """Counts how many times synthesize() is called."""

    def __init__(self) -> None:
        self.call_count = 0

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        options: object = None,
    ) -> SynthesizedAudio:
        self.call_count += 1
        return SynthesizedAudio(
            audio_bytes=text.encode(),
            sample_rate_hz=22050,
            channels=1,
            sample_width_bytes=2,
        )


# ---------------------------------------------------------------------------
# Protocol compatibility
# ---------------------------------------------------------------------------

def test_caching_engine_is_protocol_compatible() -> None:
    cache, _ = _make_cache()
    assert isinstance(cache, TextToSpeechEngine)


# ---------------------------------------------------------------------------
# Basic caching behaviour
# ---------------------------------------------------------------------------

def test_first_call_delegates_to_inner_engine() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    result = cache.synthesize("hello")

    assert inner.call_count == 1
    assert result.audio_bytes == b"hello"


def test_second_call_for_same_text_is_served_from_cache() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    first = cache.synthesize("hello")
    second = cache.synthesize("hello")

    assert inner.call_count == 1
    assert first is second


def test_different_texts_each_invoke_inner_engine() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    cache.synthesize("hello")
    cache.synthesize("world")

    assert inner.call_count == 2
    assert cache.cache_size() == 2


def test_different_voices_are_cached_separately() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    cache.synthesize("hello", voice="en-us")
    cache.synthesize("hello", voice="en-gb")
    cache.synthesize("hello", voice="en-us")

    assert inner.call_count == 2
    assert cache.cache_size() == 2


def test_none_voice_and_explicit_none_voice_are_same_key() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    cache.synthesize("hello")
    cache.synthesize("hello", voice=None)

    assert inner.call_count == 1


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------

def test_lru_eviction_drops_least_recently_used_entry() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=3)

    # Fill the cache: entries a, b, c.
    cache.synthesize("a")
    cache.synthesize("b")
    cache.synthesize("c")
    assert cache.cache_size() == 3

    # Access "a" to refresh its recency; LRU is now "b".
    cache.synthesize("a")

    # Adding "d" should evict "b" (oldest unreferenced).
    cache.synthesize("d")
    assert cache.cache_size() == 3

    # "b" should be a cache miss and re-invoke the inner engine.
    calls_before = inner.call_count
    cache.synthesize("b")
    assert inner.call_count == calls_before + 1


def test_cache_stays_bounded_under_many_unique_entries() -> None:
    cache = CachingTextToSpeechEngine(engine=FakeTextToSpeechEngine(), max_entries=4)

    for i in range(20):
        cache.synthesize(f"entry-{i}")

    assert cache.cache_size() == 4


# ---------------------------------------------------------------------------
# cache_size and clear_cache
# ---------------------------------------------------------------------------

def test_cache_size_starts_at_zero() -> None:
    cache, _ = _make_cache()
    assert cache.cache_size() == 0


def test_clear_cache_empties_the_cache() -> None:
    cache, _ = _make_cache()
    cache.synthesize("hello")
    cache.synthesize("world")

    cache.clear_cache()

    assert cache.cache_size() == 0


def test_synthesize_after_clear_re_invokes_inner_engine() -> None:
    inner = _CountingEngine()
    cache = CachingTextToSpeechEngine(engine=inner, max_entries=8)

    cache.synthesize("hello")
    cache.clear_cache()
    cache.synthesize("hello")

    assert inner.call_count == 2


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_max_entries_of_zero_raises_value_error() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        CachingTextToSpeechEngine(engine=FakeTextToSpeechEngine(), max_entries=0)


def test_negative_max_entries_raises_value_error() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        CachingTextToSpeechEngine(engine=FakeTextToSpeechEngine(), max_entries=-1)


# ---------------------------------------------------------------------------
# create_tts_engine integration
# ---------------------------------------------------------------------------

def test_create_tts_engine_wraps_in_cache_when_cache_enabled() -> None:
    config = TextToSpeechConfig(engine="fake", cache_enabled=True, cache_max_entries=16)

    engine = create_tts_engine(config)

    assert isinstance(engine, CachingTextToSpeechEngine)
    assert engine.max_entries == 16
    assert isinstance(engine.engine, FakeTextToSpeechEngine)


def test_create_tts_engine_does_not_wrap_when_cache_disabled() -> None:
    config = TextToSpeechConfig(engine="fake", cache_enabled=False)

    engine = create_tts_engine(config)

    assert isinstance(engine, FakeTextToSpeechEngine)


def test_create_tts_engine_cached_fake_synthesizes_correctly() -> None:
    config = TextToSpeechConfig(engine="fake", cache_enabled=True, cache_max_entries=4)

    engine = create_tts_engine(config)
    result = engine.synthesize("the time is noon")

    assert isinstance(result, SynthesizedAudio)
    assert result.audio_bytes == b"the time is noon"
