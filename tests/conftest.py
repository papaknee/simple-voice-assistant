"""Shared pytest fixtures for fake runtime and component reuse."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from assistant_core.fakes import FakeIntentRouter, FakeSpeechToTextEngine
from assistant_core.models import AssistantContext
from tests.fixtures.runtime import RuntimeHarness, build_runtime_harness


@pytest.fixture
def runtime_harness() -> RuntimeHarness:
    """Default fake runtime harness for unit and integration tests."""
    return build_runtime_harness()


@pytest.fixture
def runtime_harness_factory() -> Callable[..., RuntimeHarness]:
    """Factory fixture to build runtime harness with override components."""

    def _factory(
        *,
        context: AssistantContext | None = None,
        stt: FakeSpeechToTextEngine | None = None,
        router: FakeIntentRouter | None = None,
    ) -> RuntimeHarness:
        return build_runtime_harness(context=context, stt=stt, router=router)

    return _factory
