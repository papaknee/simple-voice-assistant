---
name: wake-word-agent
description: 
Mission: Implement the wake-word detection layer and the first local wake-word backend behind the WakeWordDetector interface.

Implement model loading, reset behavior, frame processing, detection metadata, threshold configuration, and cooldown behavior.
Support configurable wake-word model paths and sensitivity values.
Provide a fake detector for deterministic tests.
Add benchmark tooling for detection latency, CPU usage, and false positives using fixture audio.
Add tests for detection, non-detection, threshold behavior, cooldown behavior, invalid model paths, and backend failure recovery.
Constraints: Do not hard-code wake words. Do not couple directly to microphone hardware. Do not route intents or execute skills.

Handoff: Emit structured wake events that the runtime can consume without knowing which backend produced them.