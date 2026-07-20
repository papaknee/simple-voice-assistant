"""Tests for audio device discovery and selection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from assistant_core.audio.devices import (
    list_audio_devices,
    select_audio_device,
)
from assistant_core.interfaces import AudioDeviceInfo
from assistant_core.models import AssistantError


class TestListAudioDevices:
    """Tests for list_audio_devices function."""

    @patch("assistant_core.audio.devices.sd")
    def test_list_input_devices(self, mock_sd: MagicMock) -> None:
        """Test listing input devices."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone USB",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

        devices = list_audio_devices(device_type="input")

        assert len(devices) == 1
        assert devices[0].name == "Microphone USB"
        assert devices[0].input is True
        assert devices[0].output is False
        assert devices[0].channels == 2

    @patch("assistant_core.audio.devices.sd")
    def test_list_output_devices(self, mock_sd: MagicMock) -> None:
        """Test listing output devices."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone USB",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

        devices = list_audio_devices(device_type="output")

        assert len(devices) == 1
        assert devices[0].name == "Speakers"
        assert devices[0].input is False
        assert devices[0].output is True
        assert devices[0].channels == 2

    @patch("assistant_core.audio.devices.sd")
    def test_list_all_devices(self, mock_sd: MagicMock) -> None:
        """Test listing all devices."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone USB",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000,
            },
        ]

        devices = list_audio_devices(device_type="both")

        assert len(devices) == 2

    @patch("assistant_core.audio.devices.sd")
    def test_single_device_response(self, mock_sd: MagicMock) -> None:
        """Test handling when sounddevice returns a single dict instead of list."""
        mock_sd.query_devices.return_value = {
            "name": "Microphone",
            "max_input_channels": 1,
            "max_output_channels": 0,
            "default_samplerate": 16000,
        }

        devices = list_audio_devices()

        assert len(devices) == 1
        assert devices[0].name == "Microphone"

    @patch("assistant_core.audio.devices.sd")
    def test_device_defaults(self, mock_sd: MagicMock) -> None:
        """Test that defaults are used when values are missing."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Device",
                "max_input_channels": 1,
                "max_output_channels": 0,
            }
        ]

        devices = list_audio_devices()

        assert len(devices) == 1
        assert devices[0].sample_rate_hz == 16000
        assert devices[0].channels == 1

    @patch("assistant_core.audio.devices.sd")
    def test_device_id_assignment(self, mock_sd: MagicMock) -> None:
        """Test that device IDs are assigned correctly."""
        mock_sd.query_devices.return_value = [
            {"name": "Device 0", "max_input_channels": 1, "max_output_channels": 0},
            {"name": "Device 1", "max_input_channels": 1, "max_output_channels": 0},
            {"name": "Device 2", "max_input_channels": 0, "max_output_channels": 1},
        ]

        devices = list_audio_devices()

        assert devices[0].device_id == "0"
        assert devices[1].device_id == "1"
        assert devices[2].device_id == "2"

    def test_sounddevice_not_installed(self) -> None:
        """Test error handling when sounddevice is not available."""
        with patch.dict("sys.modules", {"sounddevice": None}):
            with pytest.raises(AssistantError) as exc_info:
                list_audio_devices()
            assert exc_info.value.code == "audio.sounddevice_not_available"

    @patch("assistant_core.audio.devices.sd")
    def test_device_query_error(self, mock_sd: MagicMock) -> None:
        """Test error handling when device query fails."""
        mock_sd.query_devices.side_effect = RuntimeError("Device enumeration failed")

        with pytest.raises(AssistantError) as exc_info:
            list_audio_devices()
        assert exc_info.value.code == "audio.device_query_failed"


class TestSelectAudioDevice:
    """Tests for select_audio_device function."""

    @patch("assistant_core.audio.devices.sd")
    def test_select_by_device_id(self, mock_sd: MagicMock) -> None:
        """Test selecting device by numeric ID."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
            {
                "name": "Speakers",
                "max_input_channels": 0,
                "max_output_channels": 1,
                "default_samplerate": 16000,
            },
        ]

        device = select_audio_device("1", device_type="output")

        assert device.name == "Speakers"
        assert device.device_id == "1"

    @patch("assistant_core.audio.devices.sd")
    def test_select_by_exact_name(self, mock_sd: MagicMock) -> None:
        """Test selecting device by exact name."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone USB",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]

        device = select_audio_device("Microphone USB", device_type="input")

        assert device.name == "Microphone USB"

    @patch("assistant_core.audio.devices.sd")
    def test_select_by_partial_name(self, mock_sd: MagicMock) -> None:
        """Test selecting device by partial name match."""
        mock_sd.query_devices.return_value = [
            {
                "name": "USB Audio Device - Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]

        device = select_audio_device("USB", device_type="input")

        assert "USB" in device.name

    @patch("assistant_core.audio.devices.sd")
    def test_select_case_insensitive(self, mock_sd: MagicMock) -> None:
        """Test that device name selection is case-insensitive."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone USB",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]

        device = select_audio_device("microphone usb", device_type="input")

        assert device.name == "Microphone USB"

    @patch("assistant_core.audio.devices.sd")
    def test_select_default_device_none(self, mock_sd: MagicMock) -> None:
        """Test selecting default device when identifier is None."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Default Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
            {
                "name": "Other Mic",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]
        mock_sd.default.device = (0, 1)

        device = select_audio_device(None, device_type="input")

        assert device.device_id == "0"

    @patch("assistant_core.audio.devices.sd")
    def test_device_not_found_by_id(self, mock_sd: MagicMock) -> None:
        """Test error when device ID is not found."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]

        with pytest.raises(AssistantError) as exc_info:
            select_audio_device("999", device_type="input")
        assert exc_info.value.code == "audio.device_not_found_by_id"

    @patch("assistant_core.audio.devices.sd")
    def test_device_not_found_by_name(self, mock_sd: MagicMock) -> None:
        """Test error when device name is not found."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]

        with pytest.raises(AssistantError) as exc_info:
            select_audio_device("NonExistent", device_type="input")
        assert exc_info.value.code == "audio.device_not_found_by_name"

    @patch("assistant_core.audio.devices.sd")
    def test_no_default_device(self, mock_sd: MagicMock) -> None:
        """Test error when no default device is configured."""
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone",
                "max_input_channels": 1,
                "max_output_channels": 0,
                "default_samplerate": 16000,
            },
        ]
        mock_sd.default.device = (None, None)

        with pytest.raises(AssistantError) as exc_info:
            select_audio_device(None, device_type="input")
        assert exc_info.value.code == "audio.no_default_device"


class TestAudioDeviceInfo:
    """Tests for AudioDeviceInfo dataclass."""

    def test_audio_device_info_creation(self) -> None:
        """Test creating AudioDeviceInfo instances."""
        device = AudioDeviceInfo(
            device_id="0",
            name="Test Microphone",
            sample_rate_hz=48000,
            channels=2,
            input=True,
            output=False,
        )

        assert device.device_id == "0"
        assert device.name == "Test Microphone"
        assert device.sample_rate_hz == 48000
        assert device.channels == 2
        assert device.input is True
        assert device.output is False

    def test_audio_device_info_defaults(self) -> None:
        """Test AudioDeviceInfo default values."""
        device = AudioDeviceInfo(
            device_id="1",
            name="Speaker",
            sample_rate_hz=16000,
            channels=1,
        )

        assert device.input is False
        assert device.output is False
