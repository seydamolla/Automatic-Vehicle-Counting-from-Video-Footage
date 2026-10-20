"""Video processing service built on Ultralytics YOLO and ByteTrack."""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, cast

from vehicle_counter.counter import Direction, LineCounter, LineSegment


@dataclass(frozen=True, slots=True)
class ProcessingOptions:
    """Normalized counting-line and detector settings."""

    line_x1: float
    line_y1: float
    line_x2: float
    line_y2: float
    confidence: float = 0.25
    model_name: str = "yolo11n.pt"

    def __post_init__(self) -> None:
        values = (self.line_x1, self.line_y1, self.line_x2, self.line_y2)
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("Çizgi koordinatları 0 ile 1 arasında olmalıdır.")
        if self.line_x1 == self.line_x2 and self.line_y1 == self.line_y2:
            raise ValueError("Sayım çizgisinin başlangıç ve bitiş noktaları farklı olmalıdır.")
        if not 0.05 <= self.confidence <= 0.95:
            raise ValueError("Güven eşiği 0.05 ile 0.95 arasında olmalıdır.")
        if self.model_name not in {"yolo11n.pt", "yolo11s.pt", "yolo11m.pt"}:
            raise ValueError("Desteklenmeyen model seçimi.")


@dataclass(frozen=True, slots=True)
class VideoResult:
    """Files and metrics produced for a processed video."""

    source_name: str
    annotated_path: Path
    csv_path: Path
    positive_count: int
    negative_count: int
    processed_frames: int
    elapsed_seconds: float

    @property
    def fps(self) -> float:
        """Return average processing speed."""
        return self.processed_frames / self.elapsed_seconds if self.elapsed_seconds > 0 else 0.0


class VideoProcessor(Protocol):
    """Interface used by the web layer and lightweight test doubles."""

    def process(
        self, input_path: Path, output_dir: Path, options: ProcessingOptions
    ) -> VideoResult:
        """Process one video and return its generated files and summary."""
        ...


class UltralyticsVideoProcessor:
    """Process traffic video frames with YOLO tracking and line counting."""

    vehicle_class_ids = {2, 5, 7}  # COCO: car, bus, truck

    def process(  # pragma: no cover - requires the external model and video codec
        self, input_path: Path, output_dir: Path, options: ProcessingOptions
    ) -> VideoResult:
        """Create an annotated MP4 and a crossing-event CSV for one video."""
        try:
            import cv2
            from ultralytics import YOLO  # type: ignore[attr-defined]
        except ImportError as exc:  # pragma: no cover - deployment guard
            raise RuntimeError("YOLO/OpenCV bağımlılıkları kurulmamış.") from exc

        capture = cv2.VideoCapture(str(input_path))
        if not capture.isOpened():
            raise ValueError(f"Video açılamadı: {input_path.name}")

        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        source_fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        if width <= 0 or height <= 0:
            capture.release()
            raise ValueError(f"Video boyutları okunamadı: {input_path.name}")

        output_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = output_dir / f"{input_path.stem}_isaretli.mp4"
        temporary_path = output_dir / f".{input_path.stem}_gecici.mp4"
        csv_path = output_dir / f"{input_path.stem}_sayim.csv"
        writer = cv2.VideoWriter(
            str(temporary_path),
            cv2.VideoWriter_fourcc(*"mp4v"),  # type: ignore[attr-defined]
            source_fps,
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise RuntimeError("İşaretli video dosyası oluşturulamadı.")

        line = LineSegment(
            (options.line_x1 * width, options.line_y1 * height),
            (options.line_x2 * width, options.line_y2 * height),
        )
        counter = LineCounter(line=line, deadband=max(2.0, height * 0.004))
        model = YOLO(options.model_name)
        events: list[dict[str, str | int | float]] = []
        frame_index = 0
        started = perf_counter()

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index += 1
                result = cast(
                    Any,
                    model.track(
                        frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=sorted(self.vehicle_class_ids),
                        conf=options.confidence,
                        verbose=False,
                    )[0],  # type: ignore[index]
                )
                annotated = result.plot()
                boxes = result.boxes
                if boxes.id is not None:
                    xyxy = boxes.xyxy.cpu().tolist()
                    identities = boxes.id.int().cpu().tolist()
                    class_ids = boxes.cls.int().cpu().tolist()
                    for box, track_id, class_id in zip(xyxy, identities, class_ids, strict=True):
                        x1, _y1, x2, y2 = box
                        direction = counter.update(track_id, ((x1 + x2) / 2, y2))
                        if direction is not None:
                            events.append(
                                {
                                    "frame": frame_index,
                                    "second": round(frame_index / source_fps, 3),
                                    "track_id": track_id,
                                    "vehicle_class": str(result.names[class_id]),
                                    "direction": direction.value,
                                }
                            )
                start = (int(line.start[0]), int(line.start[1]))
                end = (int(line.end[0]), int(line.end[1]))
                cv2.line(annotated, start, end, (0, 220, 255), 3)
                label = (
                    f"Pozitif: {counter.counts['positive']}  "
                    f"Negatif: {counter.counts['negative']}"
                )
                cv2.rectangle(annotated, (12, 12), (470, 54), (12, 24, 38), -1)
                cv2.putText(
                    annotated,
                    label,
                    (24, 42),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    2,
                )
                writer.write(annotated)
        finally:
            capture.release()
            writer.release()

        elapsed = perf_counter() - started
        self._make_browser_compatible(temporary_path, annotated_path)
        self._write_csv(csv_path, events, counter.counts, frame_index, elapsed)
        return VideoResult(
            source_name=input_path.name,
            annotated_path=annotated_path,
            csv_path=csv_path,
            positive_count=counter.counts[Direction.POSITIVE.value],
            negative_count=counter.counts[Direction.NEGATIVE.value],
            processed_frames=frame_index,
            elapsed_seconds=elapsed,
        )

    @staticmethod
    def _make_browser_compatible(source: Path, destination: Path) -> None:
        """Transcode OpenCV output to H.264 for reliable browser playback."""
        import imageio_ffmpeg  # type: ignore[import-untyped]

        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(destination),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Video tarayıcı biçimine dönüştürülemedi: {message}") from exc
        finally:
            source.unlink(missing_ok=True)

    @staticmethod
    def _write_csv(
        path: Path,
        events: list[dict[str, str | int | float]],
        counts: dict[str, int],
        frame_count: int,
        elapsed: float,
    ) -> None:
        """Write event rows followed by a machine-readable summary."""
        fieldnames = ["frame", "second", "track_id", "vehicle_class", "direction"]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)
            handle.write("\nmetric,value\n")
            handle.write(f"positive,{counts['positive']}\n")
            handle.write(f"negative,{counts['negative']}\n")
            handle.write(f"total,{counts['positive'] + counts['negative']}\n")
            handle.write(f"processed_frames,{frame_count}\n")
            handle.write(f"elapsed_seconds,{elapsed:.3f}\n")
            speed = frame_count / elapsed if elapsed > 0 else 0.0
            handle.write(f"processing_fps,{speed:.3f}\n")
