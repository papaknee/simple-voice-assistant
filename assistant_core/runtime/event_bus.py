"""In-memory event bus implementation for runtime orchestration and tests."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from assistant_core.interfaces import RuntimeEventBus, RuntimeEventHandler
from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType


class InMemoryRuntimeEventBus(RuntimeEventBus):
    """In-process runtime event bus with event history recording."""

    def __init__(self) -> None:
        self._handlers: dict[RuntimeEventType, list[RuntimeEventHandler]] = defaultdict(list)
        self._history: list[RuntimeEvent] = []

    def publish(self, event: RuntimeEvent) -> None:
        self.record(event)
        handlers = tuple(self._handlers.get(event.event_type, ()))
        for handler in handlers:
            handler(event)

    def subscribe(self, event_type: RuntimeEventType, handler: RuntimeEventHandler) -> None:
        self._handlers[event_type].append(handler)

    def record(self, event: RuntimeEvent) -> None:
        self._history.append(event)

    def history(self) -> tuple[RuntimeEvent, ...]:
        """Return recorded events in publication order."""
        return tuple(self._history)

    def clear(self) -> None:
        """Clear all subscribers and recorded history."""
        self._handlers.clear()
        self._history.clear()

    def subscribers_for(self, event_type: RuntimeEventType) -> Iterable[RuntimeEventHandler]:
        """Return current subscribers for inspection/debugging."""
        return tuple(self._handlers.get(event_type, ()))
