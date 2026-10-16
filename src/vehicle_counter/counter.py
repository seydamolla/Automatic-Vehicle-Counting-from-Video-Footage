"""Deterministic, per-track virtual-line crossing counter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import hypot


Point = tuple[float, float]


class Direction(StrEnum):
    """Direction relative to the configured directed line."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass(frozen=True, slots=True)
class LineSegment:
    """A directed virtual counting line."""

    start: Point
    end: Point

    def signed_side(self, point: Point) -> float:
        """Return the 2D cross product locating ``point`` relative to the line."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        return dx * (point[1] - self.start[1]) - dy * (point[0] - self.start[0])

    def projection(self, point: Point) -> float:
        """Return the unbounded line projection used to reject crossings outside the segment."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            raise ValueError("Counting line endpoints must differ.")
        return ((point[0] - self.start[0]) * dx + (point[1] - self.start[1]) * dy) / length_squared

    def signed_distance(self, point: Point) -> float:
        """Return perpendicular signed distance from the infinite line in pixels."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = hypot(dx, dy)
        if length == 0:
            raise ValueError("Counting line endpoints must differ.")
        return self.signed_side(point) / length


@dataclass(slots=True)
class TrackState:
    """Last stable side observed for one tracker identity."""

    stable_side: int | None = None
    counted: bool = False


@dataclass(slots=True)
class LineCounter:
    """Count each track at most once when it crosses a finite line segment.

    A deadband prevents near-line jitter from creating an artificial crossing.
    """

    line: LineSegment
    deadband: float = 2.0
    projection_margin: float = 0.05
    _tracks: dict[int, TrackState] = field(default_factory=dict, init=False)
    _counts: dict[Direction, int] = field(
        default_factory=lambda: {Direction.POSITIVE: 0, Direction.NEGATIVE: 0}, init=False
    )

    def update(self, track_id: int, bottom_center: Point) -> Direction | None:
        """Process one observed track point and return a newly counted direction.

        Args:
            track_id: Stable identifier emitted by the object tracker.
            bottom_center: Bottom-center point of the detected bounding box.

        Returns:
            The counted direction, or ``None`` if no new crossing occurred.
        """
        side_value = self.line.signed_distance(bottom_center)
        current_side = 1 if side_value > self.deadband else -1 if side_value < -self.deadband else 0
        state = self._tracks.setdefault(track_id, TrackState())
        if current_side == 0:
            return None
        if state.stable_side is None:
            state.stable_side = current_side
            return None
        direction: Direction | None = None
        if not state.counted and state.stable_side != current_side:
            crossing_projection = self.line.projection(bottom_center)
            if -self.projection_margin <= crossing_projection <= 1 + self.projection_margin:
                direction = Direction.POSITIVE if state.stable_side < current_side else Direction.NEGATIVE
                self._counts[direction] += 1
                state.counted = True
        state.stable_side = current_side
        return direction

    @property
    def counts(self) -> dict[str, int]:
        """Return a JSON/CSV-friendly snapshot of directional counts."""
        return {direction.value: count for direction, count in self._counts.items()}

