"""FastAPI web application for VisionFlow vehicle counting."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vehicle_counter.processing import (
    ProcessingOptions,
    UltralyticsVideoProcessor,
    VideoProcessor,
)

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
MAX_FILES = 5


def _safe_stem(filename: str, index: int) -> str:
    """Return a filesystem-safe, non-empty base name."""
    stem = Path(filename).stem
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    return normalized[:80] or f"video_{index}"


async def _save_upload(upload: UploadFile, destination: Path) -> None:
    """Stream an uploaded video to disk with a strict size limit."""
    written = 0
    with destination.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                handle.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Video 500 MB sınırını aşıyor.")
            handle.write(chunk)
    await upload.close()


def create_app(processor: VideoProcessor | None = None, output_root: Path | None = None) -> FastAPI:
    """Build the application with injectable processing dependencies."""
    service = processor or UltralyticsVideoProcessor()
    resolved_output = output_root or Path(
        os.getenv("VISIONFLOW_OUTPUT_DIR", str(DEFAULT_OUTPUT_ROOT))
    )
    resolved_output.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="VisionFlow Araç Sayımı", version="0.2.0")
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    app.mount("/outputs", StaticFiles(directory=resolved_output), name="outputs")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/process")
    async def process_videos(
        files: Annotated[list[UploadFile], File(...)],
        line_x1: Annotated[float, Form(...)],
        line_y1: Annotated[float, Form(...)],
        line_x2: Annotated[float, Form(...)],
        line_y2: Annotated[float, Form(...)],
        confidence: Annotated[float, Form()] = 0.25,
        model_name: Annotated[str, Form()] = "yolo11n.pt",
    ) -> dict[str, object]:
        if not files or len(files) > MAX_FILES:
            raise HTTPException(status_code=400, detail="Bir seferde 1-5 video yükleyin.")
        try:
            options = ProcessingOptions(
                line_x1=line_x1,
                line_y1=line_y1,
                line_x2=line_x2,
                line_y2=line_y2,
                confidence=confidence,
                model_name=model_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        job_id = uuid4().hex
        job_dir = resolved_output / job_id
        upload_dir = job_dir / "uploads"
        result_dir = job_dir / "results"
        upload_dir.mkdir(parents=True)
        result_dir.mkdir(parents=True)
        results: list[dict[str, object]] = []
        try:
            for index_number, upload in enumerate(files, start=1):
                original_name = upload.filename or f"video_{index_number}.mp4"
                extension = Path(original_name).suffix.lower()
                if extension not in ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=415,
                        detail=f"Desteklenmeyen dosya türü: {extension or 'uzantısız'}",
                    )
                input_path = upload_dir / f"{_safe_stem(original_name, index_number)}{extension}"
                await _save_upload(upload, input_path)
                result = await run_in_threadpool(service.process, input_path, result_dir, options)
                results.append(
                    {
                        "source_name": result.source_name,
                        "positive_count": result.positive_count,
                        "negative_count": result.negative_count,
                        "total_count": result.positive_count + result.negative_count,
                        "processed_frames": result.processed_frames,
                        "processing_fps": round(result.fps, 2),
                        "annotated_url": (
                            f"/outputs/{job_id}/results/{result.annotated_path.name}"
                        ),
                        "csv_url": f"/outputs/{job_id}/results/{result.csv_path.name}",
                    }
                )
        except HTTPException:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise
        except (RuntimeError, ValueError) as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        shutil.rmtree(upload_dir, ignore_errors=True)
        return {"job_id": job_id, "results": results}

    return app


app = create_app()


def run() -> None:
    """Start the development server."""
    import uvicorn

    uvicorn.run("vehicle_counter.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
