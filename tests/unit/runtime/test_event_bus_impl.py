"""Tests for in-memory runtime event bus behavior."""

from __future__ import annotations

from assistant_core.runtime.event_bus import InMemoryRuntimeEventBus
from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType, RuntimeState


def test_event_bus_publish_records_and_notifies_subscribers() -> None:
    bus = InMemoryRuntimeEventBus()
    seen: list[RuntimeEventType] = []

    def on_wake(event: RuntimeEvent) -> None:
        seen.append(event.event_type)

    bus.subscribe(RuntimeEventType.WAKE_DETECTED, on_wake)
    event = RuntimeEvent(RuntimeEventType.WAKE_DETECTED, RuntimeState.IDLE_LISTENING)
    bus.publish(event)

    assert seen == [RuntimeEventType.WAKE_DETECTED]
    assert bus.history() == (event,)


def test_event_bus_record_tracks_without_dispatch() -> None:
    bus = InMemoryRuntimeEventBus()
    seen: list[RuntimeEventType] = []

    def on_state_change(event: RuntimeEvent) -> None:
        seen.append(event.event_type)

    bus.subscribe(RuntimeEventType.STATE_TRANSITIONED, on_state_change)
    event = RuntimeEvent(RuntimeEventType.STATE_TRANSITIONED, RuntimeState.BOOT)
    bus.record(event)

    assert seen == []
    assert bus.history() == (event,)


def test_event_bus_clear_removes_subscribers_and_history() -> None:
    bus = InMemoryRuntimeEventBus()
    bus.subscribe(RuntimeEventType.WAKE_DETECTED, lambda event: None)
    bus.publish(RuntimeEvent(RuntimeEventType.WAKE_DETECTED, RuntimeState.IDLE_LISTENING))

    assert bus.history()
    assert tuple(bus.subscribers_for(RuntimeEventType.WAKE_DETECTED))

    bus.clear()

    assert bus.history() == ()
    assert tuple(bus.subscribers_for(RuntimeEventType.WAKE_DETECTED)) == ()
