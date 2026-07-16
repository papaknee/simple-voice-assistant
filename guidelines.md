# Shared Agent Guidelines

Use this document as common context for all work on the modular edge Python voice assistant. The complete scope and backlog remain in [simple assistant spec.md](simple%20assistant%20spec.md) and [WORK_PLAN.md](WORK_PLAN.md).

## Product Direction

- Build a simple, extensible, configurable, privacy-conscious voice assistant for Linux edge hardware.
- Target Python 3.11+ and Raspberry Pi 4-class devices without depending on Raspberry Pi-only APIs.
- The default path must work locally and offline after setup. Cloud integrations are optional adapters and must be explicitly enabled.
- Prioritize a reliable command pipeline before conversational AI or a graphical interface.
- Users must customize wake words, models, devices, voices, sounds, skills, and logging through configuration and assets, not core-code edits.

## Architecture Boundaries

The event-driven pipeline is:

`audio input -> wake word -> VAD/recording -> STT -> intent routing -> skill execution -> response generation -> TTS -> audio output`

- Keep each stage independently replaceable behind small typed interfaces.
- Use typed dataclasses, protocols or abstract contracts, dependency injection, and structured events/errors.
- Do not create global singletons or let an adapter depend directly on unrelated pipeline stages.
- Backends may not bypass the runtime to invoke concrete implementations directly.
- Skills return structured results only. They do not speak, play sounds, exit the process, or mutate global runtime state.
- Runtime behavior is a testable state machine: Boot, IdleListening, Activated, CapturingCommand, Transcribing, RoutingIntent, ExecutingSkill, Responding, Recovering, Shutdown.

## Configuration and Privacy

- Never hard-code wake words, device names, model paths, sound paths, voices, skill names, or user-specific paths.
- Make defaults explicit and validate configuration with actionable error messages.
- New configuration fields require schema validation, sample configuration, tests, and documentation in the same change set.
- Do not load large models during configuration validation.
- Audio and transcripts stay local by default. Do not store either unless explicit configuration permits it.
- Logs should include lifecycle, state-transition, timing, and actionable error details; redact sensitive content by default.

## Reliability and Hardware

- Keep hardware-specific behavior inside audio or backend adapters; support standard Linux audio stacks and device selection by name or index.
- Failures in audio, models, or skills must return structured errors and allow the daemon to recover to listening state when possible.
- Avoid indefinite blocking, high idle CPU use, unnecessary model loading, and avoidable memory growth.
- Mark physical-device tests separately so normal development and CI do not require hardware or internet access.

## Implementation Standards

- Keep changes scoped to the assigned issue. Do not perform cross-cutting rewrites without approval.
- Python code must use 3.11+ typing, small focused modules, and clear public contracts.
- Add external dependencies only when justified. Backend dependencies must be optional unless needed by the core runtime.
- Prefer existing interfaces and shared test utilities over parallel abstractions or duplicate fakes.
- Preserve backwards-compatible configuration unless a documented migration is included.
- Treat shared interface changes as architecture work and coordinate them before changing subsystem code.

## Testing and Documentation

- Every feature needs unit tests and, when applicable, a fixture-based or integration test.
- Use fake audio, wake, VAD, STT, intent, skill, TTS, and playback components for deterministic default tests.
- Test both expected behavior and failures: missing devices/assets/models, empty transcripts, timeouts, disabled skills, permission denials, and recovery paths.
- Update relevant documentation with every behavior or configuration change. Do not document unimplemented features as available.

## Collaboration and Handoffs

- Check [WORK_PLAN.md](WORK_PLAN.md) for ownership and dependencies before starting work.
- Do not claim a task until its blocking dependencies are complete, unless its plan explicitly permits parallel work with fakes.
- If blocked by a missing decision, model, hardware asset, or upstream contract, record the blocker and provide a fake or fixture path where practical.
- If integration exposes a contract mismatch, create a targeted issue for the owning subsystem instead of rewriting both sides.
- In the final handoff, list changed files, tests added and run, known limitations, configuration changes, and notes for dependent agents.