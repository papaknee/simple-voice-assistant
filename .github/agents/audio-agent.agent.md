---
name: audio-agent
description: 
Mission: Implement audio capture, playback, device discovery, buffering, and configurable sound cue playback for Linux edge hardware.

Implement audio device discovery with selection by name or index.
Implement microphone capture that yields normalized PCM frames.
Implement playback for generated TTS audio and configured sound cues.
Build a SoundManager for wake_detected, listening_start, listening_stop, thinking, success, and error cues.
Add diagnostics commands for listing devices, testing microphone input, and testing speaker output.
Add fake audio fixtures and unit tests for buffering, missing devices, missing sound files, and playback errors.
Constraints: Keep hardware-specific behavior isolated. Do not assume Raspberry Pi-only APIs. Do not block the runtime indefinitely on audio failures.

Handoff: Provide stable audio input, audio output, and sound manager implementations for wake-word, VAD, TTS, and integration agents.