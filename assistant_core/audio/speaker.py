"""Audio output (playback) adapter using sounddevice library."""

from __future__ import annotations

from assistant_core.audio.devices import select_audio_device
from assistant_core.interfaces import AudioDeviceInfo, AudioOutput, SynthesizedAudio


class SoundDeviceAudioOutput(AudioOutput):
    """Speaker playback using sounddevice library."""

    def __init__(
        self,
        device_identifier: str | None = None,
        sample_rate_hz: int = 16000,
        channels: int = 1,
    ) -> None:
        """Initialize speaker output adapter.

        Args:
            device_identifier: Device ID or name (None for default).
            sample_rate_hz: Target sample rate in Hz.
            channels: Number of audio channels.
        """
        self.device_identifier = device_identifier
        self.sample_rate_hz = sample_rate_hz
        self.channels = channels
        self._device_info: AudioDeviceInfo | None = None

    def play(self, audio: SynthesizedAudio) -> None:
        """Play synthesized audio through speaker.

        Args:
            audio: SynthesizedAudio containing PCM data and metadata.

        Raises:
            AssistantError: If audio playback fails.
        """
        try:
            import sounddevice as sd
        except ImportError:
            raise ImportError(
                "sounddevice library is not installed. Install it with: pip install sounddevice"
            )

        try:
            # Select the device
            device_info = select_audio_device(self.device_identifier, device_type="output")
            device_id = int(device_info.device_id)

            # Convert bytes to numpy array for playback
            import numpy as np

            audio_array = np.frombuffer(audio.audio_bytes, dtype=np.int16)
            if audio.channels > 1:
                audio_array = audio_array.reshape(-1, audio.channels)

            # Play audio
            sd.play(audio_array, samplerate=audio.sample_rate_hz, device=device_id, blocking=True)

        except (ImportError, ValueError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to play audio: {e}") from e

    def stop(self) -> None:
        """Stop any currently playing audio.

        Raises:
            RuntimeError: If unable to stop playback.
        """
        try:
            import sounddevice as sd

            sd.stop()
        except ImportError:
            raise ImportError("sounddevice library is not installed.")
        except Exception as e:
            raise RuntimeError(f"Failed to stop audio playback: {e}") from e

    def device_info(self) -> AudioDeviceInfo:
        """Get device information.

        Returns:
            AudioDeviceInfo for the selected output device.

        Raises:
            AssistantError: If device cannot be found or accessed.
        """
        if self._device_info is None:
            device_info = select_audio_device(self.device_identifier, device_type="output")
            # Update stored info
            self._device_info = device_info
        return self._device_info
