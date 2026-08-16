# Build the Backend for a Local Whisper-to-Viseme Generator

Build a production-quality **Python backend** for a local audio-to-viseme generation application.

The backend must replace a Gemini-based audio analysis workflow with a completely local pipeline.

## Technology

Use:

- Python 3.11+
- FastAPI
- Uvicorn
- faster-whisper
- FFmpeg / FFprobe
- Pydantic
- PyTorch where required by the selected models
- A suitable local phoneme/forced-alignment solution
- pytest for testing

Do NOT use:

- Gemini
- OpenAI API
- cloud-based speech APIs
- LLM APIs for timestamp generation
- any paid API for the core pipeline

The application should work offline after models have been downloaded.

---

# Core Pipeline

Implement:

```text
Audio
  ↓
FFmpeg normalization
  ↓
Audio duration detection
  ↓
faster-whisper
  ↓
word timestamps
  ↓
phoneme alignment
  ↓
phoneme timestamps
  ↓
phoneme → viseme mapping
  ↓
40ms timeline generation
  ↓
JSON
```

The application must process the COMPLETE audio duration.

Whisper's last timestamp must never be considered the end of the audio.

---

# Audio Input

Support:

- WAV
- MP3
- M4A
- FLAC
- OGG

Use FFmpeg to normalize audio internally to an appropriate format, preferably:

```text
16 kHz
mono
PCM WAV
```

Never modify the original file.

Use FFprobe to determine the authoritative duration.

Example:

```bash
ffprobe -v error \
  -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.wav
```

---

# Whisper

Use `faster-whisper`.

Support configurable models:

```text
tiny
base
small
medium
large-v3
```

Default to `small` unless hardware detection suggests another sensible default.

Support:

```text
CPU
CUDA
MPS where supported
```

Expose model selection through configuration/API.

Enable word timestamps.

Return internally:

```json
{
  "segments": [],
  "words": [
    {
      "word": "hello",
      "start": 1.24,
      "end": 1.81
    }
  ]
}
```

---

# Phoneme Alignment

Whisper does NOT produce phonemes.

Implement a separate local phoneme alignment stage.

Use an appropriate local/open-source forced alignment solution.

The output should be:

```json
[
  {
    "phoneme": "h",
    "start": 1.24,
    "end": 1.31
  },
  {
    "phoneme": "ə",
    "start": 1.31,
    "end": 1.42
  }
]
```

Do not simply divide word duration evenly between letters.

Use actual phoneme alignment whenever possible.

The alignment system should be abstracted behind an interface so that it can be replaced later.

For example:

```python
class PhonemeAligner:
    def align(self, audio_path, transcription):
        ...
```

---

# Viseme Engine

Create a dedicated module:

```text
visemes/
    mapper.py
    mappings/
        en.json
```

Map phonemes to configurable visemes.

Example:

```json
{
  "p": "PP",
  "b": "PP",
  "m": "PP",

  "f": "FF",
  "v": "FF",

  "θ": "TH",
  "ð": "TH",

  "t": "DD",
  "d": "DD",

  "s": "SS",
  "z": "SS",

  "ʃ": "SH",
  "ʒ": "SH",

  "k": "KK",
  "g": "KK",
  "ŋ": "KK",

  "ɑ": "AA",
  "æ": "AA",

  "i": "E",
  "eɪ": "E",

  "ɔ": "OH",
  "oʊ": "OH",

  "u": "OO",
  "ʊ": "OO",

  "r": "RR",
  "l": "LL",

  "w": "WW",
  "j": "E"
}
```

Unknown/unmapped phonemes should have a configurable fallback.

---

# Timeline Generation

The final timeline MUST use a configurable interval.

Default:

```text
0.04 seconds
```

Generate timestamps independently of Whisper.

For duration:

```text
10.00 seconds
```

generate:

```text
0.00
0.04
0.08
...
9.96
```

For every timestamp:

1. Determine whether a phoneme is active.
2. If a phoneme is active, map it to a viseme.
3. If no phoneme is active, use `sil`.
4. Create an event.

Do not stop when Whisper stops detecting speech.

Long silence must remain represented.

For example:

```json
[
  {"time": 0.00, "viseme": "sil"},
  {"time": 0.04, "viseme": "sil"},
  ...
  {"time": 3.20, "viseme": "AA"},
  ...
  {"time": 7.20, "viseme": "sil"}
]
```

Use integer frame indexes internally rather than repeatedly adding floating-point values.

For example:

```python
time = frame_index * interval
```

---

# Processing Architecture

Use a modular architecture:

```text
app/
├── main.py
├── api/
│   ├── routes.py
│   └── schemas.py
├── audio/
│   ├── ffmpeg.py
│   └── metadata.py
├── transcription/
│   └── whisper.py
├── alignment/
│   ├── base.py
│   └── aligner.py
├── visemes/
│   ├── mapper.py
│   └── mappings/
├── timeline/
│   └── generator.py
├── jobs/
│   └── manager.py
├── models/
│   └── manager.py
└── tests/
```

Keep the components independent.

---

# REST API

Implement:

## Health

```http
GET /api/health
```

Return:

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Models

```http
GET /api/models
```

Return installed/downloadable models and their status.

## Upload

```http
POST /api/analyze
```

Accept:

```text
multipart/form-data
audio=<file>
```

Optional parameters:

```text
model
language
interval
device
smoothing
```

Return a job ID:

```json
{
  "job_id": "abc123"
}
```

Do not block the HTTP request while processing a long audio file.

---

# Job API

```http
GET /api/jobs/{job_id}
```

Return:

```json
{
  "id": "abc123",
  "status": "processing",
  "stage": "transcribing",
  "progress": 42
}
```

Stages:

```text
queued
preparing_audio
transcribing
aligning
mapping
generating_timeline
completed
error
```

When completed:

```json
{
  "id": "abc123",
  "status": "completed",
  "duration": 12.73,
  "event_count": 319
}
```

---

# Result API

```http
GET /api/jobs/{job_id}/result
```

Return:

```json
{
  "duration": 12.73,
  "interval": 0.04,
  "events": [
    {
      "time": 0.00,
      "viseme": "sil"
    }
  ]
}
```

Also expose:

```http
GET /api/jobs/{job_id}/download
```

to download the JSON file.

---

# Preview Data

The frontend needs enough information to visualize the result.

Provide an optional detailed endpoint:

```http
GET /api/jobs/{job_id}/debug
```

Return:

```json
{
  "duration": 12.73,
  "words": [],
  "phonemes": [],
  "visemes": [],
  "events": []
}
```

This endpoint can be disabled in production if necessary.

---

# Model Manager

Implement local model caching.

Models must only be downloaded once.

Track:

```text
model name
installed
download status
size
device compatibility
```

Expose this through:

```http
GET /api/models
```

---

# Configuration

Use a configuration file/environment variables.

Support:

```text
MODEL_DIR
TEMP_DIR
OUTPUT_DIR
DEFAULT_MODEL
DEFAULT_LANGUAGE
DEFAULT_INTERVAL
DEVICE
```

Do not hard-code machine-specific paths.

---

# Error Handling

Return useful errors for:

- unsupported audio
- corrupt audio
- FFmpeg missing
- model missing
- insufficient memory
- CUDA unavailable
- alignment failure
- invalid parameters

Never crash the API because one audio job failed.

---

# Cleanup

Temporary normalized audio files should be deleted after processing unless debug mode is enabled.

Provide configurable retention for completed jobs.

---

# Testing

Create tests for:

1. Normal speech.
2. Silence before speech.
3. Silence after speech.
4. Long 2–5 second pauses.
5. Silence-only audio.
6. Very short audio.
7. MP3 input.
8. WAV input.
9. M4A input.
10. FLAC input.
11. Timeline duration.
12. 40 ms spacing.
13. Phoneme mapping.
14. Unknown phonemes.
15. Failed transcription.
16. Failed alignment.

Verify that:

```text
last_event_time <= audio_duration
```

and that long silence is preserved.

For a 10-second silence-only file, the output must contain silence events for the entire timeline.

---

# CLI

Also implement:

```bash
viseme-gen input.wav --output output.json
```

Options:

```text
--model
--language
--interval
--device
--smoothing
```

The CLI must use exactly the same processing pipeline as the API.

Do not duplicate processing logic.

---

# Documentation

Create a README containing:

- installation
- FFmpeg installation
- Python setup
- model download
- CPU usage
- CUDA usage
- CLI usage
- API usage
- configuration
- troubleshooting
- architecture

Include example API requests and responses.

---

# Final Requirement

The backend must be completely functional before frontend integration.

Provide:

1. Source code.
2. requirements.txt or pyproject.toml.
3. FastAPI server.
4. CLI.
5. Tests.
6. README.
7. Example viseme mapping.
8. Example generated JSON.

The backend must not require Gemini or any paid API.