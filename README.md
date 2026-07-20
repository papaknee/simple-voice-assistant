# Simple Voice Assistant (Edge, Modular, Offline-First)

This repository tracks the development of a modular Python voice assistant for Linux edge hardware.

Current focus is foundation planning and implementation sequencing. Runtime code is not complete yet.

## Project goals

- Simple and extensible architecture with replaceable backends.
- Configuration-first customization (wake, audio, STT, TTS, skills).
- Offline-first default behavior after local setup.
- Privacy-conscious defaults (no transcript/audio retention unless explicitly enabled).

## Current status

Development is tracked in waves and dependency-gated work items:

- Work tracker: [WORK_PLAN.md](WORK_PLAN.md)
- Development specification: [simple assistant spec.md](simple%20assistant%20spec.md)
- Shared implementation guardrails: [guidelines.md](guidelines.md)
- Architecture boundaries and workflow: [docs/ARCHITECTURE_AND_WORKFLOW.md](docs/ARCHITECTURE_AND_WORKFLOW.md)
- Testing strategy and CI assumptions: [TESTING.md](TESTING.md)

## Planned architecture (high-level)

Pipeline:

`audio input -> wake word -> VAD/recording -> STT -> intent routing -> skill execution -> response generation -> TTS -> audio output`

Each stage is intended to remain independently replaceable behind typed interfaces.

## Repository layout (baseline)

```text
assistant_core/
  models.py
  interfaces.py
  fakes.py
  audio/
  wake/
  vad/
  stt/
  intent/
  skills/
  tts/
  runtime/
tests/
config/
plugins/
assets/sounds/
models/
docs/
scripts/
```

Core typed domain models and runtime event types currently live in:

- `assistant_core/models.py`
- `assistant_core/runtime/events.py`
- `assistant_core/interfaces.py`
- `assistant_core/runtime/event_bus.py`
- `assistant_core/fakes.py`
- `assistant_core/runtime/state_machine.py`
- `assistant_core/config/schema.py`
- `assistant_core/config/loader.py`
- `config/default.toml`

## Configuration loading

The configuration system supports:

- default TOML loading from `config/default.toml`
- optional user TOML overrides
- environment overrides with `ASSISTANT_<SECTION>__<KEY>`

Sample profiles are provided in `config/`:

- `development.toml`
- `reference-raspberry-pi4.toml`
- `reference-mini-pc.toml`

Examples:

- `ASSISTANT_AUDIO__SAMPLE_RATE_HZ=44100`
- `ASSISTANT_PRIVACY__STORE_TRANSCRIPTS=true`

Built-in skills are registered through `assistant_core.skills.SkillRegistry` and enabled through `skills.enabled_builtin_skills` in configuration. Skill metadata includes example utterances plus optional configuration and response-contract descriptors so intent routing and future plugin loading can consume a stable shape.

Skill execution guardrails live in `assistant_core.skills.SkillExecutor`. The default policy allows `filesystem_read` and denies dangerous permissions such as `network`, `filesystem_write`, `gpio`, `shell`, and `home_automation` unless a caller explicitly opts in.

The built-in MVP skills currently ship from `assistant_core.skills`: `TimeDateSkill` handles both `get_time` and `get_date` intents under the stable `time_date` skill identity, and `EchoDebugSkill` returns routed text for pipeline debugging. `create_builtin_skills()` returns them in the default registration order used by configuration.

## Contributing

Contribution conventions and workflow are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

In short:

1. Choose a `Ready` work item from [WORK_PLAN.md](WORK_PLAN.md).
2. Keep changes scoped to that item and its explicit dependencies.
3. Include tests/documentation updates in the same change set when behavior changes.
4. Update work item status and handoff notes when complete.

## Implementation roadmap

The roadmap is organized in waves:

- Wave 0: decisions and documentation setup
- Wave 1: core contracts, fake runtime path, config and test foundation
- Wave 2: subsystem adapters
- Wave 3: runtime assembly and customization
- Wave 4: hardware hardening and release preparation
