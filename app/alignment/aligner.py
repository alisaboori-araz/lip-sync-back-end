import os
import subprocess
import tempfile
from pathlib import Path

from app.alignment.base import AlignmentError, PhonemeAligner
from app.domain import Phoneme, Word


class MontrealForcedAligner(PhonemeAligner):
    """Adapter for the local, open-source Montreal Forced Aligner CLI.

    MFA needs an acoustic model and dictionary for the target language. It is never
    contacted as a cloud service; install/download assets once before offline use.
    """

    def __init__(
        self,
        dictionary_path: Path | None,
        acoustic_model_path: Path | None,
        conda_executable: Path | None = None,
        conda_environment: str | None = None,
        temp_dir: Path | None = None,
    ) -> None:
        self.dictionary_path = dictionary_path
        self.acoustic_model_path = acoustic_model_path
        self.conda_executable = conda_executable
        self.conda_environment = conda_environment
        self.temp_dir = temp_dir

    def _command(self) -> list[str]:
        if self.conda_executable and self.conda_environment:
            return [
                str(self.conda_executable),
                "run",
                "-n",
                self.conda_environment,
                "mfa",
            ]
        return ["mfa"]

    def align(self, audio_path: Path, words: list[Word], language: str) -> list[Phoneme]:
        if not words:
            return []
        if not self.dictionary_path or not self.acoustic_model_path:
            raise AlignmentError(
                "MFA alignment is not configured. Set MFA_DICTIONARY_PATH and "
                "MFA_ACOUSTIC_MODEL_PATH to local MFA assets."
            )
        transcript = " ".join(word.word for word in words)
        temporary_dir = str(self.temp_dir) if self.temp_dir else None
        if self.temp_dir:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="viseme-mfa-", dir=temporary_dir) as temporary:
            corpus = Path(temporary) / "corpus"
            output = Path(temporary) / "output"
            corpus.mkdir()
            (corpus / "audio.wav").write_bytes(audio_path.read_bytes())
            (corpus / "audio.lab").write_text(transcript, encoding="utf-8")
            command = [
                *self._command(), "align", str(corpus), str(self.dictionary_path),
                str(self.acoustic_model_path), str(output), "--clean", "--quiet",
            ]
            environment = os.environ.copy()
            if self.temp_dir:
                environment["TEMP"] = str(self.temp_dir.resolve())
                environment["TMP"] = environment["TEMP"]
            completed = subprocess.run(
                command, capture_output=True, text=True, check=False, env=environment
            )
            if completed.returncode:
                raise AlignmentError(f"MFA alignment failed: {completed.stderr.strip()}")
            textgrid = next(output.glob("**/*.TextGrid"), None)
            if textgrid is None:
                raise AlignmentError("MFA completed but emitted no TextGrid.")
            return self._read_phones(textgrid)

    @staticmethod
    def _read_phones(textgrid_path: Path) -> list[Phoneme]:
        try:
            from praatio import textgrid as praatio_textgrid
        except ImportError as exc:
            raise AlignmentError("Install praatio to read MFA TextGrid output.") from exc
        grid = praatio_textgrid.openTextgrid(str(textgrid_path), includeEmptyIntervals=False)
        tier = grid.getTier("phones")
        return [
            Phoneme(label, start, end)
            for start, end, label in tier.entries
            if label and label not in {"sil", "sp", "spn"}
        ]
