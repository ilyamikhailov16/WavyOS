# WavyOS Avatar Bootstrap Brief

## Context from the current codebase

WavyOS is already functioning as a local Russian-speaking desktop assistant for Windows.
Its implemented core is:

1. Speech-to-text capture in real time.
2. LLM-based mapping from user utterance to one allowed command.
3. Structured argument extraction through strict schemas.
4. Local execution of approved desktop automation tools.

This means the system already has an execution backbone.
The missing layer is the avatar layer: the visible and behavioral entity through which the user experiences the assistant.

## What already exists in the repo

- Main app runner: `main.py`
- STT and LLM post-processing: `stt/`
- Typed command schemas and registry: `commands/`
- Windows automation tools: `scripts/`
- Centralized config: `config/settings.py`
- Mascot asset: `src/images/mascot.png`

## Decision now fixed

The team decision memo is now captured in:

- `avatar/docs/avatar_decision_memo_ru.md`

Current implementation direction:

- choose a hybrid state-driven 2D avatar for the current stage
- do not start with Live2D
- use visible state changes as the primary UX value
- keep the avatar layer decoupled from STT and command execution internals

## What this new workspace should likely cover

- Avatar identity and UX role
- State machine and expression states
- Screen presence model
- Runtime loop for avatar reactions
- Event bridge from command execution to avatar state changes
- Dialogue tone and personality rules
- Future UI container for rendering the avatar on desktop

## Near-term implementation reading

Based on the decision memo, the first version of the avatar should be treated as a state-driven UX layer over the existing assistant core, not as a full social character simulation.

That means the first technical focus should be:

- clear state transitions
- lightweight rendering
- basic lip sync
- event-driven reactions to listening, thinking, speaking, command execution, and errors
