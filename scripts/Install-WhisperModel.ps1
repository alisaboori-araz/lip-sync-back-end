[CmdletBinding()]
param(
    [ValidateSet("tiny", "base", "small", "medium", "large-v3")]
    [string]$Model = "small",

    [string]$PythonExecutable
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExecutable) {
    $PythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
}

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Python was not found at '$PythonExecutable'. Create the virtual environment first, or pass -PythonExecutable."
}

$modelDir = Join-Path $projectRoot "models"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

Write-Host "Downloading faster-whisper '$Model' into $modelDir"
& $PythonExecutable -c @"
from pathlib import Path
from faster_whisper import WhisperModel

model = "$Model"
model_dir = Path(r"$modelDir")
WhisperModel(model, download_root=str(model_dir))
print(f"Ready: {model} in {model_dir.resolve()}")
"@

if ($LASTEXITCODE -ne 0) {
    throw "The '$Model' Whisper model download failed."
}

