"""Audio input/output interfaces and adapters."""

from assistant_core.audio.devices import (
    list_audio_devices,
    select_audio_device,
)
from assistant_core.audio.microphone import SoundDeviceAudioInput
from assistant_core.audio.speaker import SoundDeviceAudioOutput
from assistant_core.audio.sounds import FileSoundManager, NullSoundManager

__all__ = [
    "list_audio_devices",
    "select_audio_device",
    "SoundDeviceAudioInput",
    "SoundDeviceAudioOutput",
    "FileSoundManager",
    "NullSoundManager",
]
