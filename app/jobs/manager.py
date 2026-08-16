import json
import shutil
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.config import Settings
from app.pipeline import AnalysisPipeline


@dataclass
class Job:
    id: str
    status: str = "queued"
    stage: str = "queued"
    progress: int = 0
    duration: float | None = None
    event_count: int | None = None
    error: str | None = None
    result_path: Path | None = None
    debug: dict = field(default_factory=dict)


class JobManager:
    def __init__(self, settings: Settings, pipeline_factory) -> None:
        self.settings, self.pipeline_factory = settings, pipeline_factory
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def submit(self, source: Path, model: str, language: str, interval: float, device: str) -> Job:
        job = Job(id=uuid.uuid4().hex)
        with self.lock:
            self.jobs[job.id] = job
        threading.Thread(
            target=self._run, args=(job, source, model, language, interval, device), daemon=True
        ).start()
        return job

    def _run(self, job: Job, source: Path, model: str, language: str, interval: float, device: str) -> None:
        stages = {"preparing_audio": 15, "transcribing": 40, "aligning": 65, "mapping": 80, "generating_timeline": 90}
        normalized = self.settings.temp_dir / f"{job.id}.wav"
        try:
            job.status = "processing"
            pipeline: AnalysisPipeline = self.pipeline_factory(model, device, language)
            result = pipeline.run(source, normalized, language, interval, lambda stage: self._stage(job, stage, stages))
            visemes = [asdict(event) for event in result.events]
            payload = {
                "duration": result.duration,
                "interval": result.interval,
                "visemes": visemes,
                # Kept during the transition for clients using the original API contract.
                "events": visemes,
            }
            result_path = self.settings.output_dir / f"{job.id}.json"
            result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            job.duration, job.event_count, job.result_path = result.duration, len(result.events), result_path
            job.debug = {
                **payload,
                "words": [asdict(word) for word in result.words],
                "phonemes": [asdict(phoneme) for phoneme in result.phonemes],
            }
            job.status, job.stage, job.progress = "completed", "completed", 100
        except Exception as exc:
            job.status, job.stage, job.error = "error", "error", str(exc)
        finally:
            if not self.settings.debug:
                normalized.unlink(missing_ok=True)
                source.unlink(missing_ok=True)

    @staticmethod
    def _stage(job: Job, stage: str, stages: dict[str, int]) -> None:
        job.stage, job.progress = stage, stages[stage]

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)
