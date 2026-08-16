from pathlib import Path

from app.alignment.aligner import MontrealForcedAligner


def test_mfa_command_uses_configured_conda_environment():
    aligner = MontrealForcedAligner(
        Path("dictionary"),
        Path("acoustic"),
        Path("C:/Miniforge/condabin/conda.bat"),
        "viseme-mfa",
        Path("temp"),
    )
    assert aligner._command() == [
        "C:\\Miniforge\\condabin\\conda.bat",
        "run",
        "-n",
        "viseme-mfa",
        "mfa",
    ]


def test_reads_mfa_phone_tier(tmp_path):
    textgrid_path = tmp_path / "aligned.TextGrid"
    textgrid_path.write_text(
        """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 0.3
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 0.3
        intervals: size = 3
        intervals [1]:
            xmin = 0
            xmax = 0.1
            text = "sil"
        intervals [2]:
            xmin = 0.1
            xmax = 0.2
            text = "P"
        intervals [3]:
            xmin = 0.2
            xmax = 0.3
            text = "AA1"
""",
        encoding="utf-8",
    )
    phones = MontrealForcedAligner._read_phones(textgrid_path)
    assert [(phone.phoneme, phone.start, phone.end) for phone in phones] == [
        ("P", 0.1, 0.2),
        ("AA1", 0.2, 0.3),
    ]
