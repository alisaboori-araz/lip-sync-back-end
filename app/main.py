from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.alignment.aligner import MontrealForcedAligner
from app.api.routes import router
from app.config import settings
from app.jobs.manager import JobManager
from app.pipeline import AnalysisPipeline
from app.transcription.whisper import WhisperTranscriber


def build_pipeline(model: str, device: str, language: str) -> AnalysisPipeline:
    assets = settings.alignment_assets(language)
    return AnalysisPipeline(
        WhisperTranscriber(model, device, settings.model_dir),
        MontrealForcedAligner(
            assets.dictionary_path,
            assets.acoustic_model_path,
            settings.mfa_conda_executable,
            settings.mfa_conda_environment,
            settings.temp_dir,
        ),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    app.state.jobs = JobManager(settings, build_pipeline)
    yield


app = FastAPI(title="Local Whisper-to-Viseme API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
