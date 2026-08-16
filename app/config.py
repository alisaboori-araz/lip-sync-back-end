from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AlignmentAssets:
    def __init__(self, dictionary_path: Path | None, acoustic_model_path: Path | None) -> None:
        self.dictionary_path = dictionary_path
        self.acoustic_model_path = acoustic_model_path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_dir: Path = Path("./models")
    temp_dir: Path = Path("./data/tmp")
    output_dir: Path = Path("./data/output")
    default_model: str = "small"
    default_language: str = "en"
    default_interval: float = 0.04
    device: str = "auto"
    debug: bool = False
    job_retention_hours: int = 24
    mfa_dictionary_path: Path | None = None
    mfa_acoustic_model_path: Path | None = None
    mfa_conda_executable: Path | None = None
    mfa_conda_environment: str | None = None
    fa_mfa_dictionary_path: Path | None = None
    fa_mfa_acoustic_model_path: Path | None = None

    def ensure_directories(self) -> None:
        for path in (self.model_dir, self.temp_dir, self.output_dir):
            path.mkdir(parents=True, exist_ok=True)

    def alignment_assets(self, language: str) -> AlignmentAssets:
        if language == "en":
            return AlignmentAssets(self.mfa_dictionary_path, self.mfa_acoustic_model_path)
        if language == "fa":
            return AlignmentAssets(self.fa_mfa_dictionary_path, self.fa_mfa_acoustic_model_path)
        raise ValueError(f"Unsupported language '{language}'.")


settings = Settings()
