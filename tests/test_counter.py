"""Six acceptance scenarios specified in the week-two report."""

from vehicle_counter.counter import Direction, LineCounter, LineSegment


def make_counter() -> LineCounter:
    """Build a horizontal line spanning x=0 through x=10."""
    return LineCounter(LineSegment((0.0, 0.0), (10.0, 0.0)), deadband=0.5)


def feed(counter: LineCounter, track_id: int, points: list[tuple[float, float]]) -> list[Direction]:
    """Collect non-empty crossing events for a synthetic trajectory."""
    return [event for point in points if (event := counter.update(track_id, point)) is not None]


def test_straight_crossing_is_counted() -> None:
    assert feed(make_counter(), 1, [(5, -3), (5, 3)]) == [Direction.POSITIVE]


def test_both_directions_are_separate() -> None:
    counter = make_counter()
    assert feed(counter, 1, [(4, -2), (4, 2)]) == [Direction.POSITIVE]
    assert feed(counter, 2, [(6, 2), (6, -2)]) == [Direction.NEGATIVE]
    assert counter.counts == {"positive": 1, "negative": 1}


def test_jitter_on_line_is_not_a_crossing() -> None:
    assert feed(make_counter(), 1, [(5, -3), (5, -0.2), (5, 0.3), (5, -0.4)]) == []


def test_returning_vehicle_is_counted_once() -> None:
    assert feed(make_counter(), 1, [(5, -3), (5, 3), (5, -3)]) == [Direction.POSITIVE]


def test_crossing_outside_segment_is_ignored() -> None:
    assert feed(make_counter(), 1, [(20, -3), (20, 3)]) == []


def test_new_identity_after_crossing_does_not_duplicate_prior_track() -> None:
    counter = make_counter()
    assert feed(counter, 7, [(5, -3), (5, 3)]) == [Direction.POSITIVE]
    # A new tracker identity first observed after the line cannot reconstruct a crossing.
    assert feed(counter, 99, [(5, 3), (5, 4)]) == []
