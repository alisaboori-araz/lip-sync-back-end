# Local Whisper-to-Viseme Backend

An offline FastAPI and CLI backend that normalizes audio with FFmpeg, obtains word timestamps with `faster-whisper`, uses local Montreal Forced Aligner (MFA) for actual phoneme timestamps, then creates a complete viseme timeline at 40 ms intervals.

## Install

Install Python 3.11+ and FFmpeg (both `ffmpeg` and `ffprobe` must be on `PATH`), then:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[whisper,alignment,dev]"
copy .env.example .env
```

On Windows, install MFA through Miniforge/Conda, which includes its Kaldi runtime:

```bash
conda create -n viseme-mfa -c conda-forge montreal-forced-aligner
```

MFA is local and requires local acoustic-model and dictionary files. Set `MFA_DICTIONARY_PATH` and `MFA_ACOUSTIC_MODEL_PATH` in `.env`. Download those assets once with MFA; thereafter the pipeline operates offline. Whisper models are cached under `MODEL_DIR` when first used.

## Download the required models

The first download requires an internet connection. After these files are cached, analysis runs locally without a cloud speech or alignment service.

### Whisper transcription model

The backend defaults to the multilingual `small` CTranslate2 model published by SYSTRAN for `faster-whisper`. It downloads automatically the first time you submit an analysis job, and is then cached in `MODEL_DIR`.

To download it ahead of time, with the virtual environment active:

```bash
python -c "from faster_whisper import WhisperModel; WhisperModel('small', download_root='./models')"
```

Choose `tiny`, `base`, `small`, `medium`, or `large-v3` with the API/CLI `model` option. Download each model once in the same way by replacing `small`. The model files are sourced from the SYSTRAN `faster-whisper-*` repositories on Hugging Face; `small` is about 486 MB.

### English phoneme-alignment models

Install MFA and download a matching acoustic model plus pronunciation dictionary:

```bash
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
mfa model inspect acoustic english_us_arpa
mfa model inspect dictionary english_us_arpa
```

Then configure the names in `.env` (MFA resolves them from its local cache):

```text
MFA_ACOUSTIC_MODEL_PATH=english_us_arpa
MFA_DICTIONARY_PATH=english_us_arpa
```

### Persian / Farsi phoneme-alignment models

Persian is built into the API and CLI as `language=fa`, with its own viseme mapping at `app/visemes/mappings/fa.json`. To run Persian analysis, install or create a local MFA-compatible Persian acoustic model and matching Persian pronunciation dictionary, then set:

```text
FA_MFA_ACOUSTIC_MODEL_PATH=/path/to/persian_acoustic_model
FA_MFA_DICTIONARY_PATH=/path/to/persian_dictionary
```

These must be real local Persian alignment assets; Whisper's `fa` transcription alone does not provide phoneme timestamps.

For another language, use MFA's pretrained-model catalog to choose an acoustic model and dictionary with the same phone set, download both with `mfa model download`, and add a corresponding viseme mapping at `app/visemes/mappings/<language>.json`.

## Run

```bash
uvicorn app.main:app --reload
viseme-gen input.wav --output output.json --model small --language en
```

Upload audio without waiting for processing:

```bash
curl -F "audio=@input.wav" http://127.0.0.1:8000/api/analyze
curl http://127.0.0.1:8000/api/jobs/JOB_ID
curl -OJ http://127.0.0.1:8000/api/jobs/JOB_ID/download
```

`GET /api/health` checks the server. `GET /api/models` lists model cache status. Set `DEBUG=true` to enable `GET /api/jobs/{id}/debug`.

### Unified WebSocket

Connect once to `ws://127.0.0.1:8000/api/ws`. The socket sends health heartbeats and model-cache updates, accepts an `analyze` command followed by the audio as a binary frame, streams job status, and sends the result. See `FRONTEND_WEBSOCKET.md` for the complete message protocol and a ready-to-paste TypeScript client.

## Configuration

`MODEL_DIR`, `TEMP_DIR`, `OUTPUT_DIR`, `DEFAULT_MODEL`, `DEFAULT_LANGUAGE`, `DEFAULT_INTERVAL`, `DEVICE`, `DEBUG`, `MFA_DICTIONARY_PATH`, and `MFA_ACOUSTIC_MODEL_PATH` are environment variables. CPU uses int8 Whisper inference; CUDA uses float16. `mps` is accepted but currently falls back to CPU because faster-whisper/CTranslate2 does not provide native MPS execution.

On Windows, use `MFA_CONDA_EXECUTABLE` and `MFA_CONDA_ENVIRONMENT` when MFA is installed through Miniforge/Conda. This makes the backend run MFA with Conda's required DLL paths without requiring the server itself to be started from an activated Conda shell.

## Architecture

`app/audio` owns FFmpeg/FFprobe, `transcription` owns Whisper, `alignment` owns MFA, `visemes` maps phonemes, `timeline` independently covers the FFprobe duration, and `jobs` runs the shared `pipeline` in the background. The API and CLI use that same pipeline; no cloud or paid APIs are used.

## Tests

```bash
pytest
```

The unit tests cover timeline duration, spacing, silence coverage, and mapping. Integration tests for actual audio formats require FFmpeg plus downloaded Whisper/MFA assets and should be run in the deployment environment.
