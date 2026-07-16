# Contributing Conventions

This project is organized around dependency-aware work items in [WORK_PLAN.md](WORK_PLAN.md).

## Workflow

1. Select a work item with status `Ready`.
2. Confirm all listed dependencies are `Done`.
3. Claim the item and move it to `In progress`.
4. Deliver implementation + tests + docs updates required by that item.
5. Validate changes using available project checks.
6. Update handoff notes and move status to `Review`, `Validation`, or `Done` as appropriate.

## Scope and boundaries

- Keep changes focused on the assigned item. Avoid cross-cutting rewrites.
- Preserve modular boundaries. Backends should remain behind interfaces.
- Prefer dependency injection over global state.
- Do not hard-code wake words, devices, model paths, voices, sound paths, or user-specific paths.
- Keep cloud integrations out of the default runtime path unless explicitly requested.

## Testing expectations

- Add or update unit tests for behavior changes.
- Add fixture-based/integration coverage where practical.
- Cover failure handling for your subsystem (for example: invalid config, missing assets, timeouts, empty outputs).
- Keep hardware-dependent tests opt-in.

## Documentation expectations

- Update user/developer docs in the same change set as behavior or configuration changes.
- Do not document unimplemented features as available.
- Keep examples and defaults aligned with current implementation.

## Handoff requirements

In task handoff notes (and PR descriptions), include:

- changed files
- tests added
- tests run
- known limitations or blockers
- configuration changes
- dependency notes for downstream agents
