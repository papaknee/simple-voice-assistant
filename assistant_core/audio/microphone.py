"""Microphone capture adapter using sounddevice library."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

from assistant_core.audio.devices import select_audio_device
from assistant_core.interfaces import AudioDeviceInfo, AudioInput
from assistant_core.models import AssistantError


@dataclass(slots=True)
class SoundDeviceAudioInput(AudioInput):
    """Microphone capture using sounddevice library with frame buffering."""

    device_identifier: str | None
    sample_rate_hz: int = 16000
    channels: int = 1
    sample_width_bytes: int = 2
    buffer_size_frames: int = 4096
    _stream: object | None = None
    _running: bool = False
    _buffer: deque[bytes] = None  # type: ignore
    _lock: threading.Lock = None  # type: ignore
    _device_info: AudioDeviceInfo | None = None

    def __post_init__(self) -> None:
        """Initialize mutable fields after dataclass creation."""
        object.__setattr__(self, "_buffer", deque(maxlen=self.buffer_size_frames))
        object.__setattr__(self, "_lock", threading.Lock())

    def start(self) -> None:
        """Start microphone capture stream."""
        if self._running:
            raise RuntimeError("AudioInput is already running.")

        try:
            import sounddevice as sd
        except ImportError:
            raise AssistantError(
                code="audio.sounddevice_not_available",
                message="sounddevice library is not installed. Install it with: pip install sounddevice",
            )

        try:
            # Select the device
            device_info = select_audio_device(self.device_identifier, device_type="input")
            object.__setattr__(self, "_device_info", device_info)

            # Create and start the stream
            device_id = int(device_info.device_id)

            def audio_callback(indata: object, frames: int, time_info: object, status: object) -> None:
                """Callback for audio stream."""
                if status:
                    # Log status but don't fail (underflow/overflow are common)
                    pass
                # Store the audio data as bytes
                audio_bytes = bytes(indata)  # type: ignore
                with self._lock:
                    self._buffer.append(audio_bytes)

            stream = sd.InputStream(
                device=device_id,
                channels=self.channels,
                samplerate=self.sample_rate_hz,
                blocksize=self.sample_rate_hz // 10,  # 100ms blocks
                callback=audio_callback,
                dtype="int16",
            )
            stream.start()
            object.__setattr__(self, "_stream", stream)
            object.__setattr__(self, "_running", True)

        except AssistantError:
            raise
        except Exception as e:
            raise AssistantError(
                code="audio.stream_start_failed",
                message=f"Failed to start audio stream: {e}",
            ) from e

    def stop(self) -> None:
        """Stop microphone capture stream."""
        if not self._running:
            return

        try:
            if self._stream is not None:
                stream = self._stream
                stream.stop()  # type: ignore
                stream.close()  # type: ignore
            object.__setattr__(self, "_stream", None)
            object.__setattr__(self, "_running", False)
        except Exception as e:
            raise AssistantError(
                code="audio.stream_stop_failed",
                message=f"Failed to stop audio stream: {e}",
            ) from e

    def read_frames(self, *, max_frames: int | None = None) -> bytes:
        """Read buffered audio frames."""
        if not self._running:
            raise RuntimeError("AudioInput must be started before reading frames.")

        result = b""
        frames_to_read = max_frames if max_frames is not None else len(self._buffer)

        with self._lock:
            for _ in range(min(frames_to_read, len(self._buffer))):
                frame = self._buffer.popleft()
                result += frame

        return result

    def device_info(self) -> AudioDeviceInfo:
        """Get device information."""
        if self._device_info is None:
            # If not started yet, select device to get info
            device_info = select_audio_device(self.device_identifier, device_type="input")
            return device_info
        return self._device_info
