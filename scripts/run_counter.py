"""Process one video from the command line."""

from __future__ import annotations

import argparse
from pathlib import Path

from vehicle_counter.processing import ProcessingOptions, UltralyticsVideoProcessor


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument(
        "--line",
        nargs=4,
        type=float,
        default=(0.1, 0.65, 0.9, 0.65),
        metavar=("X1", "Y1", "X2", "Y2"),
        help="Normalized line coordinates between 0 and 1.",
    )
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/cli"))
    return parser.parse_args()


def main() -> None:
    """Run the processor and print a concise result."""
    args = parse_args()
    options = ProcessingOptions(*args.line, confidence=args.confidence, model_name=args.model)
    result = UltralyticsVideoProcessor().process(args.video, args.output_dir, options)
    print(
        f"Tamamlandı: +{result.positive_count} / -{result.negative_count} "
        f"({result.fps:.2f} FPS)"
    )
    print(f"Video: {result.annotated_path}")
    print(f"CSV: {result.csv_path}")


if __name__ == "__main__":
    main()
