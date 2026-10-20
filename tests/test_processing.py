"""Tests for processing configuration and result serialization."""

from pathlib import Path

import pytest

from vehicle_counter.processing import ProcessingOptions, UltralyticsVideoProcessor, VideoResult


def test_processing_options_accept_valid_defaults() -> None:
    options = ProcessingOptions(0.1, 0.5, 0.9, 0.5)
    assert options.model_name == "yolo11n.pt"
    assert options.confidence == 0.25


@pytest.mark.parametrize(
    "arguments, message",
    [
        ((-0.1, 0.5, 0.9, 0.5), "0 ile 1"),
        ((0.5, 0.5, 0.5, 0.5), "farklı"),
        ((0.1, 0.5, 0.9, 0.5, 0.01), "Güven"),
        ((0.1, 0.5, 0.9, 0.5, 0.25, "unknown.pt"), "model"),
    ],
)
def test_processing_options_reject_invalid_values(
    arguments: tuple[object, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ProcessingOptions(*arguments)  # type: ignore[arg-type]


def test_video_result_fps_handles_elapsed_time() -> None:
    result = VideoResult("a.mp4", Path("a.mp4"), Path("a.csv"), 2, 1, 50, 2.0)
    assert result.fps == 25.0
    stopped = VideoResult("b.mp4", Path("b.mp4"), Path("b.csv"), 0, 0, 0, 0.0)
    assert stopped.fps == 0.0


def test_csv_contains_events_and_summary(tmp_path: Path) -> None:
    path = tmp_path / "counts.csv"
    events: list[dict[str, str | int | float]] = [
        {
            "frame": 25,
            "second": 1.0,
            "track_id": 7,
            "vehicle_class": "car",
            "direction": "positive",
        }
    ]
    UltralyticsVideoProcessor._write_csv(
        path, events, {"positive": 1, "negative": 0}, frame_count=50, elapsed=2.0
    )
    content = path.read_text(encoding="utf-8-sig")
    assert "25,1.0,7,car,positive" in content
    assert "total,1" in content
    assert "processing_fps,25.000" in content
