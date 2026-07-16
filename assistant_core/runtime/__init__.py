"""Runtime orchestration, lifecycle, and state machine components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from assistant_core.runtime.event_bus import InMemoryRuntimeEventBus
    from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType, RuntimeState
    from assistant_core.runtime.state_machine import AssistantRuntime

__all__ = [
    "AssistantRuntime",
    "InMemoryRuntimeEventBus",
    "RuntimeEvent",
    "RuntimeEventType",
    "RuntimeState",
]


def __getattr__(name: str) -> Any:
    if name in {"RuntimeEvent", "RuntimeEventType", "RuntimeState"}:
        from assistant_core.runtime.events import RuntimeEvent, RuntimeEventType, RuntimeState

        return {
            "RuntimeEvent": RuntimeEvent,
            "RuntimeEventType": RuntimeEventType,
            "RuntimeState": RuntimeState,
        }[name]
    if name == "InMemoryRuntimeEventBus":
        from assistant_core.runtime.event_bus import InMemoryRuntimeEventBus

        return InMemoryRuntimeEventBus
    if name == "AssistantRuntime":
        from assistant_core.runtime.state_machine import AssistantRuntime

        return AssistantRuntime
    raise AttributeError(name)
