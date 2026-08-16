import shutil
import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse

from app.api.schemas import HealthResponse
from app.config import settings
from app.transcription.whisper import VALID_DEVICES, VALID_MODELS
from app.visemes.mapper import VisemeMapper

router = APIRouter(prefix="/api")
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
LANGUAGE_ALIASES = {
    "en": "en",
    "en-us": "en",
    "english": "en",
    "fa": "fa",
    "fa-ir": "fa",
    "farsi": "fa",
    "persian": "fa",
}
BACKEND_HEARTBEAT_SECONDS = 3


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


def model_list() -> list[dict]:
    return [
        {
            "name": model,
            "installed": (settings.model_dir / f"models--Systran--faster-whisper-{model}").exists(),
            "downloading": False,
        }
        for model in VALID_MODELS
    ]


def normalize_analysis_options(
    filename: str,
    model: str,
    language: str,
    interval: float,
    device: str,
) -> tuple[str, str, float, str, str]:
    suffix = Path(filename).suffix.lower()
    model = model.lower()
    language = LANGUAGE_ALIASES.get(language.lower(), language.lower())
    device = device.lower()
    # The backend stores seconds; the current frontend sends whole milliseconds
    # (for example, 40 for a 40 ms timeline interval).
    if interval > 1:
        interval /= 1000
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported audio type '{suffix or 'unknown'}'.")
    if model not in VALID_MODELS or device not in VALID_DEVICES or not 0.005 <= interval <= 1:
        raise ValueError("Invalid model, device, or interval.")
    if language not in VisemeMapper.supported_languages():
        raise ValueError(f"Unsupported language '{language}'. Supported languages: en, fa.")
    return suffix, model, language, interval, device


@router.get("/models")
def models() -> list[dict]:
    return model_list()


@router.post("/analyze", status_code=202)
async def analyze(
    request: Request,
    audio: UploadFile = File(...),
    model: str = Form(settings.default_model),
    language: str = Form(settings.default_language),
    interval: float = Form(settings.default_interval),
    device: str = Form(settings.device),
    smoothing: bool | None = Form(None),
) -> dict:
    try:
        suffix, model, language, interval, device = normalize_analysis_options(
            audio.filename or "", model, language, interval, device
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    source = settings.temp_dir / f"upload-{__import__('uuid').uuid4().hex}{suffix}"
    with source.open("wb") as output:
        shutil.copyfileobj(audio.file, output)
    manager = request.app.state.jobs
    job = manager.submit(source, model, language, interval, device)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
def job_status(request: Request, job_id: str) -> dict:
    job = request.app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return serialize_job(job)


def serialize_job(job) -> dict:
    client_status = {"queued": "pending", "error": "failed"}.get(job.status, job.status)
    response = {"id": job.id, "status": client_status, "stage": job.stage, "progress": job.progress}
    if job.status == "completed":
        response.update(duration=job.duration, event_count=job.event_count)
    if job.status == "error":
        response["error"] = job.error
    return response


def _completed_job(request: Request, job_id: str):
    job = request.app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    if job.status != "completed":
        raise HTTPException(409, f"Job is {job.status}.")
    return job


@router.get("/jobs/{job_id}/result")
def result(request: Request, job_id: str) -> FileResponse:
    job = _completed_job(request, job_id)
    return FileResponse(job.result_path, media_type="application/json", filename=f"{job_id}.json")


@router.get("/jobs/{job_id}/download")
def download(request: Request, job_id: str) -> FileResponse:
    return result(request, job_id)


@router.get("/jobs/{job_id}/debug")
def debug(request: Request, job_id: str) -> dict:
    if not settings.debug:
        raise HTTPException(404, "Debug endpoint is disabled.")
    return _completed_job(request, job_id).debug


@router.websocket("/ws")
async def backend_updates(websocket: WebSocket) -> None:
    """A single socket for health, models, upload, job progress, and results."""
    await websocket.accept()
    previous_models = None
    previous_job_payload = None
    active_job = None
    pending_upload = None
    next_heartbeat = 0.0
    try:
        while True:
            now = time.monotonic()
            if now >= next_heartbeat:
                await websocket.send_json(
                    {"type": "health", "health": {"status": "ok", "version": "1.0.0"}}
                )
                next_heartbeat = now + BACKEND_HEARTBEAT_SECONDS

            current_models = model_list()
            fingerprint = json.dumps(current_models, sort_keys=True)
            if fingerprint != previous_models:
                await websocket.send_json({"type": "models", "models": current_models})
                previous_models = fingerprint

            if active_job:
                job_payload = serialize_job(active_job)
                job_fingerprint = json.dumps(job_payload, sort_keys=True)
                if job_fingerprint != previous_job_payload:
                    await websocket.send_json({"type": "status", "job": job_payload})
                    previous_job_payload = job_fingerprint
                if active_job.status == "completed":
                    result_payload = json.loads(active_job.result_path.read_text(encoding="utf-8"))
                    await websocket.send_json(
                        {"type": "result", "job_id": active_job.id, "result": result_payload}
                    )
                    active_job = None
                    previous_job_payload = None
                elif active_job.status == "error":
                    await websocket.send_json(
                        {"type": "error", "job": job_payload, "error": active_job.error}
                    )
                    active_job = None
                    previous_job_payload = None

            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=0.2)
            except TimeoutError:
                continue
            if message["type"] == "websocket.disconnect":
                return

            if message.get("text") is not None:
                try:
                    command = json.loads(message["text"])
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "Commands must be valid JSON."})
                    continue
                if command.get("type") != "analyze":
                    await websocket.send_json(
                        {"type": "error", "error": "Unsupported command. Send type 'analyze'."}
                    )
                    continue
                if active_job or pending_upload:
                    await websocket.send_json(
                        {"type": "error", "error": "This socket already has an active upload or job."}
                    )
                    continue
                try:
                    pending_upload = normalize_analysis_options(
                        str(command.get("file_name", "")),
                        str(command.get("model", settings.default_model)),
                        str(command.get("language", settings.default_language)),
                        float(command.get("interval", settings.default_interval)),
                        str(command.get("device", settings.device)),
                    )
                except (TypeError, ValueError) as exc:
                    await websocket.send_json({"type": "error", "error": str(exc)})
                    continue
                await websocket.send_json({"type": "upload_ready"})
                continue

            if message.get("bytes") is not None:
                if pending_upload is None:
                    await websocket.send_json(
                        {"type": "error", "error": "Send an analyze command before the audio bytes."}
                    )
                    continue
                suffix, model, language, interval, device = pending_upload
                source = settings.temp_dir / f"upload-{uuid.uuid4().hex}{suffix}"
                source.write_bytes(message["bytes"])
                active_job = websocket.app.state.jobs.submit(
                    source, model, language, interval, device
                )
                pending_upload = None
                previous_job_payload = None
                await websocket.send_json({"type": "accepted", "job": serialize_job(active_job)})
    except WebSocketDisconnect:
        return
