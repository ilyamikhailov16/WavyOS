from __future__ import annotations


class AvatarLipSync:
    """Simple amplitude-driven mouth controller for MVP rendering."""

    def __init__(
        self,
        quiet_threshold: float = 0.2,
        loud_threshold: float = 0.6,
    ) -> None:
        self.quiet_threshold = quiet_threshold
        self.loud_threshold = loud_threshold

    def level_from_amplitude(self, amplitude: float | None) -> int:
        if amplitude is None or amplitude <= 0:
            return 0
        if amplitude < self.quiet_threshold:
            return 0
        if amplitude < self.loud_threshold:
            return 1
        return 2

    def pulse_level(self, now: float) -> int:
        phase = int(now * 4) % 3
        return (0, 1, 2)[phase]
