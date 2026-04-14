# Avatar Runtime Notes

## What is implemented in MVP

- avatar state machine with states:
  - `IDLE`
  - `LISTENING`
  - `THINKING`
  - `EXECUTING`
  - `SPEAKING`
  - `ERROR`
- `AvatarService` as the single integration point for the main app
- simple amplitude-based lip sync with 3 mouth levels
- lightweight `tkinter` renderer using the existing mascot image
- headless/null renderer for tests and non-GUI fallback

## Current integration points

- `main.py`
  - creates the avatar service
  - starts and stops it with the app lifecycle
  - sends command started / succeeded / failed / rejected events
- `stt/voice_recording.py`
  - emits STT lifecycle statuses:
    - `listening_started`
    - `recording_stopped`
    - `transcription_started`
    - `processing_error`

## Important MVP limitation

The current project does not have a full TTS/voice-response pipeline.
Because of that, `SPEAKING` is implemented as a supported state and public API, but it is not deeply wired into a real audio output loop yet.

This is intentional:

- no fake heavy character system is introduced
- no extra TTS stack is forced into the project
- the architecture remains ready for future speaking integration

## Extension guidance

- add richer asset packs by extending only the renderer
- add emotions by expanding controller input and snapshot data
- add memory/planner/personality later without changing the current event bridge
- replace `TkAvatarRenderer` with Live2D later while preserving `AvatarService` and `AvatarController`
