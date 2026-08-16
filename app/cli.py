import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.alignment.aligner import MontrealForcedAligner
from app.config import settings
from app.pipeline import AnalysisPipeline
from app.transcription.whisper import WhisperTranscriber
from app.visemes.mapper import VisemeMapper


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local viseme timeline from audio.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=settings.default_model)
    parser.add_argument("--language", default=settings.default_language)
    parser.add_argument("--interval", type=float, default=settings.default_interval)
    parser.add_argument("--device", default=settings.device)
    parser.add_argument("--smoothing", type=float, default=None, help="Reserved for a later smoothing policy.")
    args = parser.parse_args()
    settings.ensure_directories()
    normalized = settings.temp_dir / f"{args.input.stem}.normalized.wav"
    if args.language not in VisemeMapper.supported_languages():
        parser.error(f"Unsupported language '{args.language}'. Supported languages: en, fa.")
    assets = settings.alignment_assets(args.language)
    pipeline = AnalysisPipeline(
        WhisperTranscriber(args.model, args.device, settings.model_dir),
        MontrealForcedAligner(
            assets.dictionary_path,
            assets.acoustic_model_path,
            settings.mfa_conda_executable,
            settings.mfa_conda_environment,
            settings.temp_dir,
        ),
    )
    try:
        result = pipeline.run(args.input, normalized, args.language, args.interval)
        args.output.write_text(json.dumps({
            "duration": result.duration, "interval": result.interval,
            "events": [asdict(event) for event in result.events],
        }, indent=2), encoding="utf-8")
    finally:
        if not settings.debug:
            normalized.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
