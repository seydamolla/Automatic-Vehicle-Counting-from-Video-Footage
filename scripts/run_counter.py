"""Run YOLO tracking and write annotated video plus directional CSV results."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
from ultralytics import YOLO

from vehicle_counter.counter import LineCounter, LineSegment


VEHICLE_CLASS_IDS = {2, 5, 7}  # COCO: car, bus, truck


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--line", nargs=4, type=float, required=True, metavar=("X1", "Y1", "X2", "Y2"))
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    return parser.parse_args()


def main() -> None:
    """Track vehicles and count their first virtual-line crossing."""
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counter = LineCounter(LineSegment((args.line[0], args.line[1]), (args.line[2], args.line[3])))
    model = YOLO(args.model)
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise FileNotFoundError(f"Cannot open video: {args.video}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(args.output_dir / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        result = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)[0]
        if result.boxes.id is not None:
            for box, track_id, class_id in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.id.int().cpu().tolist(), result.boxes.cls.int().cpu().tolist(), strict=True):
                if class_id not in VEHICLE_CLASS_IDS:
                    continue
                x1, _y1, x2, y2 = box
                counter.update(track_id, ((x1 + x2) / 2, y2))
        cv2.line(frame, tuple(map(int, args.line[:2])), tuple(map(int, args.line[2:])), (0, 255, 255), 2)
        cv2.putText(frame, f"+ {counter.counts['positive']}  - {counter.counts['negative']}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        writer.write(frame)
    capture.release()
    writer.release()
    with (args.output_dir / "counts.csv").open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows([("direction", "count"), *counter.counts.items()])


if __name__ == "__main__":
    main()

