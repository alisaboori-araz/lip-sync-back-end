# Adding Other Languages

The backend is designed to support multiple languages, but its first complete configuration is English.

Changing the API `language` value alone is not enough. A language needs all three components below:

1. Whisper transcription support.
2. A local phoneme aligner with a matching acoustic model and pronunciation dictionary.
3. A phoneme-to-viseme mapping for the language.

No cloud speech API or paid service is required.

## What works today

The initial configuration supports English:

```text
language=en
MFA_ACOUSTIC_MODEL_PATH=english_us_arpa
MFA_DICTIONARY_PATH=english_us_arpa
```

The English viseme mapping is in:

```text
app/visemes/mappings/en.json
```

## Adding a language with MFA assets

Use this path when Montreal Forced Aligner (MFA) provides, or you have created, a local acoustic model and a compatible pronunciation dictionary for the target language.

### 1. Download or prepare the alignment assets

Find a matching acoustic model and dictionary. Their phone sets must be compatible.

For an MFA-hosted model, download both into MFA's local cache:

```bash
mfa model download acoustic YOUR_ACOUSTIC_MODEL
mfa model download dictionary YOUR_DICTIONARY
```

Set the local model names or paths in `.env`:

```text
MFA_ACOUSTIC_MODEL_PATH=YOUR_ACOUSTIC_MODEL
MFA_DICTIONARY_PATH=YOUR_DICTIONARY
```

If the new language will run alongside English, the backend should next be extended to select these settings per language instead of using one global pair of MFA settings.

### 2. Add a viseme mapping

Create:

```text
app/visemes/mappings/<language-code>.json
```

For example, a file for Spanish could be named:

```text
app/visemes/mappings/es.json
```

The keys must match the phoneme labels emitted by the selected aligner. MFA models may use IPA symbols or ARPAbet-like labels. The mapper removes trailing stress digits, so `AA1` matches an `aa` key.

Example:

```json
{
  "p": "PP",
  "b": "PP",
  "m": "PP",
  "f": "FF",
  "v": "FF",
  "a": "AA",
  "e": "E",
  "i": "E",
  "o": "OH",
  "u": "OO",
  "r": "RR",
  "l": "LL"
}
```

Use `sil` as the fallback for unknown sounds until a deliberate viseme choice is made.

### 3. Test the complete pipeline

Use audio with known speech, silence before and after speech, and a long pause. Check that:

- Whisper returns the intended transcript language.
- MFA emits phonemes rather than failing on vocabulary.
- phoneme labels are covered by the new mapping.
- the event list continues through the duration reported by FFprobe.
- unknown phonemes fall back safely to `sil`.

## Persian / Farsi

Persian is built in as a supported API/CLI language:

```text
language=fa
```

The repository includes a Persian viseme mapping:

```text
app/visemes/mappings/fa.json
```

It does not bundle a Persian forced-alignment model or pronunciation dictionary. Configure local Persian MFA assets:

```text
FA_MFA_ACOUSTIC_MODEL_PATH=/path/to/persian_acoustic_model
FA_MFA_DICTIONARY_PATH=/path/to/persian_dictionary
```

If MFA-compatible Persian assets are unavailable, provide:

- another local phoneme aligner that implements `PhonemeAligner` in `app/alignment/base.py`.

The aligner must return real phoneme timestamps:

```python
[
    {"phoneme": "…", "start": 0.0, "end": 0.08}
]
```

Do not generate Persian phoneme timings by splitting word durations evenly.

## Supporting another local aligner

Create an implementation of `PhonemeAligner`:

```python
from pathlib import Path

from app.alignment.base import PhonemeAligner
from app.domain import Phoneme, Word


class MyLanguageAligner(PhonemeAligner):
    def align(
        self, audio_path: Path, words: list[Word], language: str
    ) -> list[Phoneme]:
        # Run the local model and return measured phoneme intervals.
        ...
```

Wire it into `build_pipeline` in `app/main.py`, selecting it by language. Keep the rest of the pipeline unchanged: normalized WAV -> transcription -> phonemes -> visemes -> complete timeline.

## Recommended implementation order

1. Add the language's local acoustic/dictionary assets or a local aligner.
2. Record the actual phoneme symbols that it produces.
3. Add the language's viseme mapping.
4. Add unit tests for its mapping and unknown phonemes.
5. Run a real audio integration test including leading, internal, and trailing silence.
