"""
Phase transition detection.

Monitors metric time series for abrupt changes that indicate
regime shifts — polarization spikes, institutional collapse,
cascade events, entropy drops, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PhaseEvent:
    """A detected phase transition event."""
    timestep: int
    metric_name: str
    event_type: str            # "spike", "drop", "threshold_crossed"
    magnitude: float           # How large the change was
    description: str = ""


class PhaseTransitionDetector:
    """Detect abrupt changes in metric time series."""

    def __init__(
        self,
        derivative_threshold: float = 2.0,
        window_size: int = 5,
    ) -> None:
        self._threshold = derivative_threshold
        self._window = window_size
        self._history: dict[str, list[float]] = {}

    def update(self, metrics: dict[str, float], timestep: int) -> list[PhaseEvent]:
        """Process one timestep of metrics and return any detected events."""
        events: list[PhaseEvent] = []

        for name, value in metrics.items():
            if name not in self._history:
                self._history[name] = []
            series = self._history[name]
            series.append(value)

            if len(series) < 2 * self._window:
                continue

            # Compute local derivative (rate of change)
            # Non-overlapping windows for clean comparison
            recent = series[-self._window:]
            baseline = series[-2 * self._window:-self._window]

            mean_recent = sum(recent) / len(recent)
            mean_baseline = sum(baseline) / len(baseline)

            if mean_baseline == 0:
                continue

            rate_of_change = abs(mean_recent - mean_baseline) / abs(mean_baseline)

            if rate_of_change > self._threshold:
                direction = "spike" if mean_recent > mean_baseline else "drop"
                events.append(PhaseEvent(
                    timestep=timestep,
                    metric_name=name,
                    event_type=direction,
                    magnitude=rate_of_change,
                    description=f"{name} {direction}: {rate_of_change:.2f}x change over {self._window} steps",
                ))

        return events

    def reset(self) -> None:
        self._history.clear()
