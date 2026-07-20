"""Audio device discovery and selection utilities."""

from __future__ import annotations

from typing import Literal

from assistant_core.interfaces import AudioDeviceInfo


def list_audio_devices(
    device_type: Literal["input", "output", "both"] = "both",
) -> list[AudioDeviceInfo]:
    """
    List available audio devices on the system.

    Args:
        device_type: Filter devices by type ("input", "output", or "both").

    Returns:
        List of AudioDeviceInfo objects for available devices.

    Raises:
        AssistantError: If device discovery fails.
    """
    devices: list[AudioDeviceInfo] = []

    try:
        import sounddevice as sd

        try:
            sd_devices = sd.query_devices()
        except Exception as e:
            raise RuntimeError(f"Failed to query audio devices: {e}") from e

        # Handle case where there's only one device
        if isinstance(sd_devices, dict):
            sd_devices = [sd_devices]

        for idx, device in enumerate(sd_devices):
            # Only include devices that are available
            if not device.get("max_input_channels", 0) and not device.get("max_output_channels", 0):
                continue

            is_input = device.get("max_input_channels", 0) > 0
            is_output = device.get("max_output_channels", 0) > 0

            # Filter by device_type
            if device_type == "input" and not is_input:
                continue
            if device_type == "output" and not is_output:
                continue

            # Use device index as ID
            device_id = str(idx)
            name = device.get("name", f"Device {idx}").strip()

            # Determine sample rate and channels (use defaults if not available)
            sample_rate_hz = int(device.get("default_samplerate", 16000))
            # Use max channels available
            channels = device.get("max_input_channels" if is_input else "max_output_channels", 1)

            audio_info = AudioDeviceInfo(
                device_id=device_id,
                name=name,
                sample_rate_hz=sample_rate_hz,
                channels=channels,
                input=is_input,
                output=is_output,
            )
            devices.append(audio_info)

        return devices

    except ImportError:
        raise ImportError(
            "sounddevice library is not installed. Install it with: pip install sounddevice"
        )


def select_audio_device(
    device_identifier: str | None,
    device_type: Literal["input", "output"],
) -> AudioDeviceInfo:
    """
    Select a specific audio device by ID or name.

    Args:
        device_identifier: Device ID (numeric string) or device name. None for default.
        device_type: Whether to select "input" or "output" device.

    Returns:
        Selected AudioDeviceInfo.

    Raises:
        AssistantError: If device not found or device discovery fails.
    """
    if device_identifier is None:
        # Return default device
        return _get_default_device(device_type)

    # Try to parse as device ID (numeric)
    try:
        device_id = int(device_identifier)
        all_devices = list_audio_devices(device_type="both")

        for device in all_devices:
            if int(device.device_id) == device_id:
                return device

        raise ValueError(f"Audio device with ID {device_id} not found.")
    except ValueError:
        # Not a numeric ID, search by name
        pass

    # Search by name (case-insensitive)
    all_devices = list_audio_devices(device_type="both")
    device_identifier_lower = device_identifier.lower()

    for device in all_devices:
        if device.name.lower() == device_identifier_lower:
            return device

    # If no exact match, try substring match
    for device in all_devices:
        if device_identifier_lower in device.name.lower():
            return device

    # Device not found
    available = ", ".join([f"{d.name} (ID: {d.device_id})" for d in all_devices])
    raise ValueError(f"Audio device '{device_identifier}' not found. Available devices: {available}")


def _get_default_device(device_type: Literal["input", "output"]) -> AudioDeviceInfo:
    """Get the default device for the specified type."""
    try:
        import sounddevice as sd

        if device_type == "input":
            device_id = sd.default.device[0]
        else:
            device_id = sd.default.device[1]

        if device_id is None or device_id < 0:
            raise RuntimeError(f"No default {device_type} device configured on system.")

        all_devices = list_audio_devices(device_type="both")
        for device in all_devices:
            if int(device.device_id) == device_id:
                return device

        raise RuntimeError(
            f"Default {device_type} device (ID: {device_id}) not found in available devices."
        )

    except ImportError:
        raise ImportError(
            "sounddevice library is not installed. Install it with: pip install sounddevice"
        )
