# Agent Guide

## Project purpose

This repository provides an offline audio-to-viseme backend. It normalizes audio
with FFmpeg, transcribes it with local `faster-whisper`, aligns words to phonemes
with local Montreal Forced Aligner (MFA), maps phonemes to visemes, and generates
a timeline. FastAPI and the CLI must use the same core pipeline.

## Environment and build

- Requires Python 3.11 or newer.
- Create and activate a virtual environment, then install development and optional
  runtime dependencies:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e ".[whisper,alignment,dev]"
  ```

- Copy `.env.example` to `.env` for local configuration. Do not commit `.env`.
- FFmpeg and FFprobe must be available on `PATH` for real audio processing.
- MFA, its acoustic model, and its pronunciation dictionary are local runtime
  dependencies. On Windows, MFA may be invoked through the configured Conda
  executable and environment.
- Whisper models, temporary uploads, generated JSON, and local MFA assets are
  runtime data. Do not add them to version control.

## Commands

- Run unit/API tests: `pytest`
- Run the API locally: `uvicorn app.main:app --reload`
- Run the CLI: `viseme-gen input.wav --output output.json --model small --language en`

Tests must remain independent of downloaded Whisper models, MFA models, FFmpeg,
and network access. Add deployment/integration checks separately when actual
external tools or models are required.

## Code structure

- `app/domain.py`: immutable shared domain dataclasses (`Word`, `Phoneme`,
  `VisemeEvent`) and analysis results.
- `app/pipeline.py`: orchestration only - audio preparation, transcription,
  alignment, mapping, and timeline generation.
- `app/audio/`: FFmpeg and audio-duration adapters.
- `app/transcription/`: local Whisper adapter and supported model/device values.
- `app/alignment/`: aligner interface and MFA implementation; isolate subprocess
  and TextGrid behavior here.
- `app/visemes/`: language-specific JSON phoneme-to-viseme mappings and loader.
- `app/timeline/`: deterministic frame-based viseme timeline generation.
- `app/jobs/`: background-job lifecycle, output serialization, and cleanup.
- `app/api/`: HTTP/WebSocket input validation, response contracts, and transport
  concerns only.
- `app/cli.py`: command-line parsing and composition of the same pipeline used by
  the API.
- `tests/`: pytest tests organized by behavioral area.

## Implementation conventions

- Keep domain behavior out of API routes and CLI argument handling. Put reusable
  logic in the relevant domain module or `AnalysisPipeline`.
- Keep external executables and optional imports behind adapter boundaries so
  ordinary tests can run without them.
- Use `pathlib.Path`, type annotations, and standard-library dataclasses, matching
  the existing style.
- Preserve the API's behavior: normalized options use seconds internally, while
  frontend millisecond interval values are accepted; client job statuses translate
  `queued` to `pending` and `error` to `failed`.
- Add a mapping file at `app/visemes/mappings/<language>.json` and matching
  configuration/alignment support before accepting a new language.
- Timeline changes must preserve complete duration coverage, frame-aligned event
  times, silence behavior, and merging of consecutive identical visemes.
- Do not silently replace the local/offline architecture with cloud services.

## Testing expectations

- Add or update focused pytest coverage for every behavior change.
- Prefer pure unit tests for timeline logic, mapping, option validation, output
  serialization, and MFA-command construction.
- Use FastAPI `TestClient` for API and WebSocket contract tests.
- Run `pytest` after changes. If tests cannot run, report the exact missing local
  dependency or environment limitation.
- Before editing, inspect `git status` and preserve unrelated user changes. Do not
  commit, push, or modify generated files unless explicitly requested.
