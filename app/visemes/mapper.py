import json
from pathlib import Path
import re


class VisemeMapper:
    @staticmethod
    def supported_languages() -> set[str]:
        return {
            path.stem
            for path in (Path(__file__).parent / "mappings").glob("*.json")
        }

    def __init__(self, language: str = "en", fallback: str = "sil") -> None:
        mapping_file = Path(__file__).parent / "mappings" / f"{language}.json"
        if not mapping_file.exists():
            raise ValueError(f"No viseme mapping exists for language '{language}'.")
        self.mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
        self.fallback = fallback

    def map(self, phoneme: str) -> str:
        normalized = re.sub(r"\d+$", "", phoneme.strip().lower().replace("ˈ", "").replace("ˌ", ""))
        return self.mapping.get(normalized, self.fallback)
