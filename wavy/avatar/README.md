# Avatar Workspace

This directory is the isolated workspace for WavyOS avatar development.

## Why it exists

The current repository already contains:
- voice input and STT processing;
- LLM-based command interpretation;
- a command registry with typed schemas;
- Windows automation tools for apps, browser, desktop, screen, and system toggles;
- a visual mascot asset in `src/images/mascot.png`.

What is still missing in code is a dedicated implementation area for the avatar itself:
- avatar runtime and state;
- emotion and expression model;
- visual rendering layer;
- dialogue/personality layer;
- integration contracts between the avatar and the existing command engine.

This folder keeps avatar work separated from the current automation core.

## Proposed structure

- `docs/` — product notes, decisions, behavior specs, research briefs
- `specs/` — technical contracts, interfaces, state models
- `src/` — avatar-specific implementation

## Current status

At the moment, the repository has only conceptual references to the avatar plus the mascot image.
This workspace was created on branch `feature/avatar-foundation` as the starting point for dedicated avatar work.

