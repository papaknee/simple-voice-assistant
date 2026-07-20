"""Sound cue manager for playing named audio files."""

from __future__ import annotations

import os
from pathlib import Path

from assistant_core.interfaces import AudioOutput, SoundManager, SynthesizedAudio
from assistant_core.models import AssistantError


class FileSoundManager(SoundManager):
    """Manages named sound cues from a filesystem directory.

    Supports loading WAV/OGG files with naming convention: {cue_name}.wav or {cue_name}.ogg
    """

    def __init__(
        self,
        sound_pack_path: str | None = None,
        audio_output: AudioOutput | None = None,
        enabled_cues: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize sound manager.

        Args:
            sound_pack_path: Path to directory containing sound files (None to use default).
            audio_output: AudioOutput adapter for playback (required for play()).
            enabled_cues: Tuple of enabled cue names. If None, all found cues are enabled.
        """
        self.sound_pack_path = sound_pack_path or self._default_sound_pack_path()
        self.audio_output = audio_output
        self.enabled_cues = enabled_cues or ()
        self._cached_cues: dict[str, str] | None = None

    def play(self, cue_name: str) -> None:
        """Play a named sound cue.

        Args:
            cue_name: Name of the sound cue to play (without extension).

        Raises:
            AssistantError: If cue not found or playback fails.
        """
        if self.audio_output is None:
            raise RuntimeError(
                "SoundManager has no AudioOutput configured for playback."
            )

        if cue_name not in self.list_available_cues():
            raise ValueError(
                f"Sound cue '{cue_name}' not found in sound pack."
            )

        try:
            audio_data = self._load_cue_audio(cue_name)
            self.audio_output.play(audio_data)
        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to play sound cue '{cue_name}': {e}") from e

    def list_available_cues(self) -> tuple[str, ...]:
        """List available sound cue names.

        Returns:
            Tuple of available cue names in enabled_cues that exist in sound pack.
        """
        if not self.enabled_cues:
            return ()

        available = []
        for cue in self.enabled_cues:
            if self._cue_file_exists(cue):
                available.append(cue)

        return tuple(available)

    def validate_pack(self) -> list[AssistantError]:
        """Validate that required sound cues are available.

        Returns:
            List of AssistantError for missing cues.
        """
        errors: list[AssistantError] = []

        if not self.sound_pack_path:
            return errors

        if not os.path.isdir(self.sound_pack_path):
            errors.append(
                AssistantError(
                    code="sound.pack_directory_not_found",
                    message=f"Sound pack directory not found: {self.sound_pack_path}",
                    details={"path": self.sound_pack_path},
                )
            )
            return errors

        missing_cues = []
        for cue in self.enabled_cues:
            if not self._cue_file_exists(cue):
                missing_cues.append(cue)

        if missing_cues:
            errors.append(
                AssistantError(
                    code="sound.required_cues_missing",
                    message=f"Required sound cues not found: {', '.join(missing_cues)}",
                    details={"missing_cues": missing_cues, "pack_path": self.sound_pack_path},
                )
            )

        return errors

    def _cue_file_exists(self, cue_name: str) -> bool:
        """Check if a cue file exists in the sound pack."""
        if not self.sound_pack_path:
            return False

        for ext in [".wav", ".ogg", ".flac", ".mp3"]:
            path = os.path.join(self.sound_pack_path, f"{cue_name}{ext}")
            if os.path.isfile(path):
                return True
        return False

    def _load_cue_audio(self, cue_name: str) -> SynthesizedAudio:
        """Load audio data for a sound cue.

        Args:
            cue_name: Name of the cue.

        Returns:
            SynthesizedAudio with the cue audio data.

        Raises:
            AssistantError: If audio cannot be loaded.
        """
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError(
                "soundfile library is not installed. Install it with: pip install soundfile"
            )

        # Find the cue file
        cue_path = None
        for ext in [".wav", ".ogg", ".flac", ".mp3"]:
            path = os.path.join(self.sound_pack_path or "", f"{cue_name}{ext}")
            if os.path.isfile(path):
                cue_path = path
                break

        if not cue_path:
            raise ValueError(
                f"Sound file for cue '{cue_name}' not found."
            )

        try:
            # Load audio with soundfile
            audio_data, sample_rate = sf.read(cue_path, dtype="int16")

            # Convert to bytes
            import numpy as np

            if isinstance(audio_data, np.ndarray):
                audio_bytes = audio_data.astype(np.int16).tobytes()
                channels = 1 if audio_data.ndim == 1 else audio_data.shape[1]
            else:
                raise ValueError(
                    f"Invalid audio format in {cue_path}"
                )

            return SynthesizedAudio(
                audio_bytes=audio_bytes,
                sample_rate_hz=int(sample_rate),
                channels=channels,
                sample_width_bytes=2,  # int16
                format="pcm_s16le",
            )

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to load sound file {cue_path}: {e}"
            ) from e

    def _default_sound_pack_path(self) -> str:
        """Get default sound pack path."""
        import assistant_core

        core_dir = os.path.dirname(assistant_core.__file__)
        return os.path.join(os.path.dirname(core_dir), "assets", "sounds")


class NullSoundManager(SoundManager):
    """No-op sound manager for when sound is disabled or unavailable."""

    def play(self, cue_name: str) -> None:
        """Do nothing."""
        pass

    def list_available_cues(self) -> tuple[str, ...]:
        """Return empty list."""
        return ()

    def validate_pack(self) -> list[AssistantError]:
        """No validation needed."""
        return []
