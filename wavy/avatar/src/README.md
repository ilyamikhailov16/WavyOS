# Avatar Source Area

This directory now contains the MVP avatar subsystem for WavyOS.

## Entry points

- `avatar_service.py` — main integration façade for the rest of the app
- `avatar_controller.py` — state machine and transition logic
- `avatar_renderer.py` — renderer interface plus simple `tkinter` MVP renderer

## How it fits the app

- `main.py` starts and stops `AvatarService`
- `stt/voice_recording.py` sends lightweight status events into the service
- command execution in `main.py` sends command lifecycle events

## Design intent

- state-driven first
- renderer replaceable
- no Live2D dependency in MVP
- testable without GUI through the null renderer

## Future Live2D path

If the project later needs Live2D, the intended replacement path is:

1. keep `AvatarController` and event contracts as-is
2. replace only the renderer implementation
3. optionally add richer emotion/state inputs without breaking the command pipeline
