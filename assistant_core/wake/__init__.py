"""Wake-word detection interfaces and adapters."""

from assistant_core.wake.detector import (
    ConfiguredWakeWordDetector,
    OpenWakeWordDetector,
    create_wake_detector,
)

__all__ = [
    "ConfiguredWakeWordDetector",
    "OpenWakeWordDetector",
    "create_wake_detector",
]
