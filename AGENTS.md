# AGENTS.md - Agent Guidance

This file should always be used as the entrypoint for agents working in this repository.

## Project Context

This repository implements `apple-compose`, a Docker Compose-like CLI for Apple Containers.

The CLI reads Compose YAML files, validates them with Pydantic models, builds an execution plan, and translates supported
Compose concepts into `container` CLI commands. It currently targets a pragmatic subset of Docker Compose rather than full
spec compatibility.

Key architecture:

- `src/apple_compose/models/` contains Pydantic models and Compose-file validation.
- `src/apple_compose/planner.py` converts validated Compose config into executable service plans.
- `src/apple_compose/container_cli.py` wraps the Apple `container` CLI.
- `src/apple_compose/commands/` contains Typer command handlers.
- `src/apple_compose/env.py` handles dotenv/env-file behavior and environment merging.

Important constraints:

- Compose-file validation belongs in Pydantic models where possible.
- Command handlers should stay thin: load config, create plans, invoke runtime wrappers.
- Keep the wrapper implementation thin and pragmatic. Do not overcomplicate `apple-compose` with abstractions or behavior
  that the Apple `container` CLI/runtime can already handle.
- Runtime errors from the Apple `container` CLI should be shown as user-facing errors, not Python traces.
- Leave most runtime error handling and validation to the Apple `container` CLI/runtime unless the wrapper has a concrete
  safety or usability reason to intervene.
- Prefer `python-dotenv`, Pydantic, Typer, and Rich instead of custom parsing/output logic when they already solve the
  problem.

## General Rules

Behavioral guidelines. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

### 5. Protect User State

**Do not disturb the user's local environment or unrelated work.**

- Use an isolated uv virtual environment outside the repository for validation commands, for example
  `UV_PROJECT_ENVIRONMENT=/tmp/project-venv uv run pytest`.
- Do not create, remove, rebuild, or modify the repository-local `.venv` unless explicitly asked.
- Do not revert, rewrite, or clean up unrelated worktree changes.
- Do not remove files or code that are outside the task scope unless they are made obsolete by your own changes.
- If a validation command would alter user state or require credentials/external services, report that instead of
  forcing it.

### 6. Validation Boundaries

**Compose-file validation belongs in Pydantic models.**

- Any validation based on data from the Docker Compose file MUST happen as part of the relevant Pydantic model.
- Field-level validation and normalization belong on the model that owns the field.
- Cross-field or cross-service validation belongs on the smallest Pydantic model that has the required context, usually
  `ComposeConfig` for service graph validation.
- Do not validate Compose-file correctness in command handlers, planners, or container runtime wrappers.
- Command handlers and planners may validate command-line input and planning context, such as unknown requested service
  names or missing CLI-provided files.
- Runtime wrappers should delegate runtime-specific validation to the underlying `container` CLI unless there is a
  concrete wrapper safety issue.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and
clarifying questions come before implementation rather than after mistakes.
