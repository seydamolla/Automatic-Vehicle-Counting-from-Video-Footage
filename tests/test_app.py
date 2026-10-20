"""End-to-end API tests using a deterministic fake video processor."""

from pathlib import Path

from fastapi.testclient import TestClient

from vehicle_counter.app import create_app
from vehicle_counter.processing import ProcessingOptions, VideoResult


class FakeProcessor:
    """Create tiny output files without loading a machine-learning model."""

    def process(
        self, input_path: Path, output_dir: Path, options: ProcessingOptions
    ) -> VideoResult:
        assert options.line_y1 == 0.65
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = output_dir / f"{input_path.stem}_isaretli.mp4"
        csv_path = output_dir / f"{input_path.stem}_sayim.csv"
        video_path.write_bytes(b"video-result")
        csv_path.write_text("direction,count\npositive,2\nnegative,1\n", encoding="utf-8")
        return VideoResult(input_path.name, video_path, csv_path, 2, 1, 75, 3.0)


def valid_form() -> dict[str, str]:
    return {
        "line_x1": "0.1",
        "line_y1": "0.65",
        "line_x2": "0.9",
        "line_y2": "0.65",
        "confidence": "0.25",
        "model_name": "yolo11n.pt",
    }


def test_health_and_home(tmp_path: Path) -> None:
    client = TestClient(create_app(FakeProcessor(), tmp_path))
    assert client.get("/api/health").json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert "VisionFlow" in response.text


def test_two_videos_are_processed_and_downloadable(tmp_path: Path) -> None:
    client = TestClient(create_app(FakeProcessor(), tmp_path))
    files = [
        ("files", ("trafik 1.mp4", b"first", "video/mp4")),
        ("files", ("trafik 2.mp4", b"second", "video/mp4")),
    ]
    response = client.post("/api/process", data=valid_form(), files=files)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 2
    assert payload["results"][0]["total_count"] == 3
    assert payload["results"][0]["processing_fps"] == 25.0
    assert client.get(payload["results"][0]["csv_url"]).status_code == 200


def test_invalid_extension_and_line_are_rejected(tmp_path: Path) -> None:
    client = TestClient(create_app(FakeProcessor(), tmp_path))
    response = client.post(
        "/api/process",
        data=valid_form(),
        files={"files": ("notes.txt", b"not-video", "text/plain")},
    )
    assert response.status_code == 415
    bad_line = valid_form() | {"line_x1": "2"}
    response = client.post(
        "/api/process",
        data=bad_line,
        files={"files": ("video.mp4", b"video", "video/mp4")},
    )
    assert response.status_code == 422
