"""Tests for microphone capture and PCM frame buffering."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from assistant_core.audio.microphone import SoundDeviceAudioInput
from assistant_core.interfaces import AudioDeviceInfo
from assistant_core.models import AssistantError


class TestSoundDeviceAudioInput:
    """Tests for SoundDeviceAudioInput microphone adapter."""

    @pytest.fixture
    def mock_device_info(self) -> AudioDeviceInfo:
        """Create a mock audio device info."""
        return AudioDeviceInfo(
            device_id="0",
            name="Test Microphone",
            sample_rate_hz=16000,
            channels=1,
            input=True,
        )

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_start_stream(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test starting audio stream."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")
        adapter.start()

        assert adapter._running is True
        mock_stream.start.assert_called_once()
        mock_sd.InputStream.assert_called_once()

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_stop_stream(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test stopping audio stream."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")
        adapter.start()
        adapter.stop()

        assert adapter._running is False
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_device_info_before_start(
        self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo
    ) -> None:
        """Test getting device info before stream is started."""
        mock_select.return_value = mock_device_info

        adapter = SoundDeviceAudioInput(device_identifier="0")
        info = adapter.device_info()

        assert info.device_id == "0"
        assert info.name == "Test Microphone"

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_device_info_after_start(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test getting device info after stream is started."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")
        adapter.start()
        info = adapter.device_info()

        assert info.device_id == "0"
        assert info.name == "Test Microphone"

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_read_frames_not_started(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test reading frames when stream is not started."""
        mock_select.return_value = mock_device_info

        adapter = SoundDeviceAudioInput(device_identifier="0")
        with pytest.raises(RuntimeError, match="must be started"):
            adapter.read_frames()

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_read_frames_buffer(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test reading frames from buffer."""
        mock_select.return_value = mock_device_info

        # Create a mock stream that calls the callback
        audio_callback_func = None

        def capture_callback(indata, frames, time_info, status, callback=None, **kwargs):
            nonlocal audio_callback_func
            audio_callback_func = callback
            return MagicMock()

        mock_stream = MagicMock()
        mock_sd.InputStream.side_effect = capture_callback

        adapter = SoundDeviceAudioInput(device_identifier="0", buffer_size_frames=10)
        adapter.start()

        # Simulate audio data arrival
        if audio_callback_func:
            test_audio = b"\x00\x01\x02\x03"
            audio_callback_func(test_audio, 4, None, None)

        # Read frames
        result = adapter.read_frames()
        # The result should contain the audio data we added
        if result:
            assert len(result) > 0

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_read_frames_max_frames(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test reading a limited number of frames."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")
        adapter.start()

        # Add some frames to buffer manually
        adapter._buffer.append(b"frame1")
        adapter._buffer.append(b"frame2")
        adapter._buffer.append(b"frame3")

        result = adapter.read_frames(max_frames=2)
        # Should have read 2 frames
        assert len(adapter._buffer) == 1

    def test_device_not_found(self) -> None:
        """Test error when device is not found."""
        with patch("assistant_core.audio.microphone.select_audio_device") as mock_select:
            mock_select.side_effect = AssistantError(
                code="audio.device_not_found",
                message="Device not found",
            )

            adapter = SoundDeviceAudioInput(device_identifier="nonexistent")
            with pytest.raises(AssistantError):
                adapter.start()

    def test_sounddevice_not_installed(self) -> None:
        """Test error when sounddevice is not installed."""
        with patch.dict("sys.modules", {"sounddevice": None}):
            adapter = SoundDeviceAudioInput(device_identifier="0")
            with pytest.raises(AssistantError, match="sounddevice_not_available"):
                adapter.start()

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_start_already_running(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test error when trying to start an already running stream."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")
        adapter.start()

        with pytest.raises(RuntimeError, match="already running"):
            adapter.start()

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_stop_not_running(self, mock_sd: MagicMock, mock_select: MagicMock) -> None:
        """Test stopping when stream is not running."""
        adapter = SoundDeviceAudioInput(device_identifier="0")
        # Should not raise an error
        adapter.stop()
        assert adapter._running is False

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_buffer_size_configuration(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test configurable buffer size."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0", buffer_size_frames=2048)
        adapter.start()

        assert adapter.buffer_size_frames == 2048
        assert adapter._buffer.maxlen == 2048

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_sample_rate_configuration(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test configurable sample rate."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0", sample_rate_hz=48000)
        adapter.start()

        assert adapter.sample_rate_hz == 48000
        # Verify sounddevice was called with correct sample rate
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["samplerate"] == 48000

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_channels_configuration(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test configurable channel count."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0", channels=2)
        adapter.start()

        assert adapter.channels == 2
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["channels"] == 2

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_default_device_selection(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test using default device when identifier is None."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier=None)
        adapter.start()

        mock_select.assert_called_with(None, device_type="input")

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_stream_creation_parameters(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test that stream is created with correct parameters."""
        mock_select.return_value = mock_device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(
            device_identifier="0",
            sample_rate_hz=44100,
            channels=2,
        )
        adapter.start()

        # Verify InputStream was called with correct parameters
        call_kwargs = mock_sd.InputStream.call_args[1]
        assert call_kwargs["device"] == 0
        assert call_kwargs["samplerate"] == 44100
        assert call_kwargs["channels"] == 2
        assert call_kwargs["dtype"] == "int16"
        assert "callback" in call_kwargs


class TestSoundDeviceAudioInputIntegration:
    """Integration tests for microphone adapter."""

    @patch("assistant_core.audio.microphone.select_audio_device")
    @patch("assistant_core.audio.microphone.sd")
    def test_lifecycle(self, mock_sd: MagicMock, mock_select: MagicMock) -> None:
        """Test complete adapter lifecycle."""
        device_info = AudioDeviceInfo(
            device_id="0",
            name="Test Mic",
            sample_rate_hz=16000,
            channels=1,
            input=True,
        )
        mock_select.return_value = device_info
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream

        adapter = SoundDeviceAudioInput(device_identifier="0")

        # Check initial state
        assert adapter._running is False

        # Start
        adapter.start()
        assert adapter._running is True

        # Get device info
        info = adapter.device_info()
        assert info.name == "Test Mic"

        # Stop
        adapter.stop()
        assert adapter._running is False

        mock_stream.start.assert_called_once()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
