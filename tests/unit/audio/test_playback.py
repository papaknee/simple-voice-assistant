"""Tests for audio output and sound management."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from assistant_core.audio.sounds import FileSoundManager, NullSoundManager
from assistant_core.audio.speaker import SoundDeviceAudioOutput
from assistant_core.interfaces import AudioDeviceInfo, SynthesizedAudio


class TestSoundDeviceAudioOutput:
    """Tests for SoundDeviceAudioOutput speaker adapter."""

    @pytest.fixture
    def mock_device_info(self) -> AudioDeviceInfo:
        """Create mock output device info."""
        return AudioDeviceInfo(
            device_id="1",
            name="Test Speaker",
            sample_rate_hz=16000,
            channels=1,
            output=True,
        )

    @pytest.fixture
    def test_audio(self) -> SynthesizedAudio:
        """Create test audio data."""
        return SynthesizedAudio(
            audio_bytes=b"\x00\x01\x02\x03",
            sample_rate_hz=16000,
            channels=1,
            sample_width_bytes=2,
        )

    @patch("assistant_core.audio.speaker.select_audio_device")
    @patch("assistant_core.audio.speaker.sd")
    def test_device_info(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test getting device info."""
        mock_select.return_value = mock_device_info

        adapter = SoundDeviceAudioOutput(device_identifier="1")
        info = adapter.device_info()

        assert info.device_id == "1"
        assert info.name == "Test Speaker"
        assert info.output is True

    @patch("assistant_core.audio.speaker.select_audio_device")
    @patch("assistant_core.audio.speaker.sd")
    def test_play_audio(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo, test_audio: SynthesizedAudio) -> None:
        """Test playing audio."""
        mock_select.return_value = mock_device_info

        adapter = SoundDeviceAudioOutput(device_identifier="1")
        adapter.play(test_audio)

        mock_sd.play.assert_called_once()

    @patch("assistant_core.audio.speaker.select_audio_device")
    @patch("assistant_core.audio.speaker.sd")
    def test_stop(self, mock_sd: MagicMock, mock_select: MagicMock) -> None:
        """Test stopping playback."""
        adapter = SoundDeviceAudioOutput(device_identifier="1")
        adapter.stop()

        mock_sd.stop.assert_called_once()

    @patch("assistant_core.audio.speaker.select_audio_device")
    def test_device_not_found(self, mock_select: MagicMock, test_audio: SynthesizedAudio) -> None:
        """Test error when device not found."""
        mock_select.side_effect = ValueError("Device not found")

        adapter = SoundDeviceAudioOutput(device_identifier="nonexistent")
        with pytest.raises(ValueError):
            adapter.play(test_audio)

    def test_sounddevice_not_installed(self, test_audio: SynthesizedAudio) -> None:
        """Test error when sounddevice not available."""
        with patch.dict("sys.modules", {"sounddevice": None}):
            adapter = SoundDeviceAudioOutput(device_identifier="0")
            with pytest.raises(ImportError):
                adapter.play(test_audio)

    @patch("assistant_core.audio.speaker.select_audio_device")
    @patch("assistant_core.audio.speaker.sd")
    def test_configuration(self, mock_sd: MagicMock, mock_select: MagicMock, mock_device_info: AudioDeviceInfo) -> None:
        """Test configurable parameters."""
        mock_select.return_value = mock_device_info

        adapter = SoundDeviceAudioOutput(
            device_identifier="1",
            sample_rate_hz=48000,
            channels=2,
        )

        assert adapter.sample_rate_hz == 48000
        assert adapter.channels == 2


class TestFileSoundManager:
    """Tests for FileSoundManager sound cue handling."""

    @pytest.fixture
    def temp_sound_pack(self) -> str:
        """Create temporary directory with test sound files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake sound files
            for cue in ["wake_detected", "listening_start", "success", "error"]:
                Path(tmpdir, f"{cue}.wav").touch()
            yield tmpdir

    @pytest.fixture
    def mock_audio_output(self) -> MagicMock:
        """Create mock audio output."""
        return MagicMock()

    def test_list_available_cues(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test listing available cues."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected", "listening_start", "success", "error"),
        )

        cues = manager.list_available_cues()

        assert "wake_detected" in cues
        assert "listening_start" in cues
        assert "success" in cues
        assert "error" in cues

    def test_list_available_cues_missing(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test listing when some cues are missing."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected", "listening_start", "nonexistent"),
        )

        cues = manager.list_available_cues()

        assert "wake_detected" in cues
        assert "listening_start" in cues
        assert "nonexistent" not in cues

    def test_validate_pack_success(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test validation when all cues present."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected", "listening_start"),
        )

        errors = manager.validate_pack()

        assert len(errors) == 0

    def test_validate_pack_missing_cues(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test validation when cues are missing."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected", "missing_cue"),
        )

        errors = manager.validate_pack()

        assert len(errors) == 1
        assert errors[0].code == "sound.required_cues_missing"

    def test_validate_pack_directory_not_found(self, mock_audio_output: MagicMock) -> None:
        """Test validation when sound pack directory doesn't exist."""
        manager = FileSoundManager(
            sound_pack_path="/nonexistent/path",
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected",),
        )

        errors = manager.validate_pack()

        assert len(errors) == 1
        assert errors[0].code == "sound.pack_directory_not_found"

    def test_play_without_audio_output(self, temp_sound_pack: str) -> None:
        """Test error when no audio output configured."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=None,
            enabled_cues=("wake_detected",),
        )

        with pytest.raises(RuntimeError, match="AudioOutput"):
            manager.play("wake_detected")

    def test_play_nonexistent_cue(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test error when playing nonexistent cue."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected",),
        )

        with pytest.raises(ValueError, match="not found"):
            manager.play("nonexistent")

    @patch("assistant_core.audio.sounds.sf")
    def test_play_success(self, mock_sf: MagicMock, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test successfully playing a cue."""
        import numpy as np

        mock_sf.read.return_value = (np.array([0, 1, 2, 3], dtype=np.int16), 16000)

        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected",),
        )

        manager.play("wake_detected")

        mock_audio_output.play.assert_called_once()
        call_arg = mock_audio_output.play.call_args[0][0]
        assert isinstance(call_arg, SynthesizedAudio)

    def test_no_cues_enabled(self, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test when no cues are enabled."""
        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=(),
        )

        cues = manager.list_available_cues()

        assert len(cues) == 0

    @patch("assistant_core.audio.sounds.sf")
    def test_stereo_audio(self, mock_sf: MagicMock, temp_sound_pack: str, mock_audio_output: MagicMock) -> None:
        """Test handling stereo audio."""
        import numpy as np

        mock_sf.read.return_value = (np.array([[0, 1], [2, 3]], dtype=np.int16), 16000)

        manager = FileSoundManager(
            sound_pack_path=temp_sound_pack,
            audio_output=mock_audio_output,
            enabled_cues=("wake_detected",),
        )

        manager.play("wake_detected")

        call_arg = mock_audio_output.play.call_args[0][0]
        assert call_arg.channels == 2


class TestNullSoundManager:
    """Tests for NullSoundManager no-op implementation."""

    def test_play_does_nothing(self) -> None:
        """Test that play() does nothing."""
        manager = NullSoundManager()
        manager.play("any_cue")  # Should not raise

    def test_list_available_cues_empty(self) -> None:
        """Test that list returns empty."""
        manager = NullSoundManager()
        cues = manager.list_available_cues()

        assert len(cues) == 0

    def test_validate_pack_empty(self) -> None:
        """Test that validation returns no errors."""
        manager = NullSoundManager()
        errors = manager.validate_pack()

        assert len(errors) == 0
