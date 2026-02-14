from __future__ import annotations

from vulture.core.events import EventBus

_EVENT_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _EVENT_BUS
    if _EVENT_BUS is None:
        _EVENT_BUS = EventBus()
    return _EVENT_BUS
