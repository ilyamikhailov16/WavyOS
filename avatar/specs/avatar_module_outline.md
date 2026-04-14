# Avatar Module Outline

## Goal

Define the future module boundary for the avatar layer without changing the existing automation core yet.

The current product decision is to build a hybrid state-driven 2D avatar first.
This spec therefore assumes:

- no Live2D runtime in the first iteration
- renderer and controller stay independent from STT internals
- avatar behavior is driven by normalized app events and state transitions

## Suggested responsibilities

- Keep avatar state.
- Convert internal events into visible reactions.
- Own UX-facing behavior for visible feedback.
- Expose a stable interface for the command engine.
- Stay replaceable so a future Live2D renderer can reuse the same controller/state logic.

## Suggested initial submodules

- `avatar_state.py` — current mode, visibility, activity, speaking intensity
- `avatar_events.py` — normalized events from STT, LLM, and command execution
- `avatar_controller.py` — state machine and transition rules
- `avatar_renderer.py` — 2D rendering of state via sprites or simple animations
- `avatar_lipsync.py` — mouth openness/intensity from audio level
- `avatar_bridge.py` — integration point with the current `App` loop

## Suggested first integration events

- listening_started
- listening_finished
- transcription_started
- command_recognized
- command_rejected
- command_started
- command_succeeded
- command_failed
- idle

## Suggested first visual states

- `idle`
- `listening`
- `thinking`
- `speaking`
- `executing`
- `error`

## First sprint scope

- formalize the avatar state machine
- define event-to-state transition rules
- implement `AvatarController`
- implement a minimal 2D renderer
- add simple lip sync based on amplitude
- keep Live2D explicitly out of scope for this iteration
