# Architecture Boundaries and Agent Contribution Workflow

This document defines the architecture constraints and delivery workflow for contributors working on this repository.

## Architecture boundaries

The assistant is organized as an event-driven pipeline:

`audio input -> wake word -> VAD/recording -> STT -> intent routing -> skill execution -> response generation -> TTS -> audio output`

Contributors should preserve these boundaries:

- Each stage remains replaceable behind typed interfaces in `assistant_core/interfaces.py`.
- Runtime orchestration stays in `assistant_core/runtime/` and should not be bypassed by adapters.
- Adapters should not directly depend on unrelated stages.
- Skills return structured results only and do not handle speech playback directly.
- Shared models and structured errors should use `assistant_core/models.py`.
- Runtime behavior should align with the state machine stages in `assistant_core/runtime/events.py` and `assistant_core/runtime/state_machine.py`.

## Configuration and privacy boundaries

- Do not hard-code wake words, model paths, device names, voices, sound cues, skill names, or user-specific paths.
- Prefer typed configuration and validation through `assistant_core/config/`.
- Keep transcript and raw audio retention disabled by default unless explicitly configured.
- Avoid loading heavy models during configuration validation.

## Agent contribution workflow

1. Pick a dependency-ready item from `WORK_PLAN.md`.
2. Confirm all listed dependencies are marked `Done`.
3. Scope changes to the assigned item; avoid cross-cutting rewrites.
4. Implement code, tests, and docs updates required by that item.
5. Run the project quality checks listed in `CONTRIBUTING.md` when code changes are involved.
6. Update `WORK_PLAN.md` status and add concise handoff notes.
7. Include changed files, tests added/run, limitations, config changes, and downstream notes in your final handoff.

## Ownership and coordination

- Treat interface or shared contract changes as architecture work and coordinate before changing multiple subsystems.
- When blocked by missing upstream contracts or assets, record the blocker and provide fixture/fake-based progress where possible.
- If integration reveals a contract mismatch, file a targeted follow-up item rather than rewriting ownership boundaries.
