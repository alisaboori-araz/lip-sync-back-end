[CmdletBinding()]
param(
    [ValidateSet("tiny", "base", "small", "medium", "large-v3")]
    [string]$WhisperModel = "small",

    [string]$Dictionary,

    [string]$AcousticModel,

    [string]$MfaCondaExecutable,

    [string]$MfaEnvironment = "viseme-mfa",

    [switch]$SkipWhisperDownload
)

$ErrorActionPreference = "Stop"

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value
    )

    $lines = if (Test-Path -LiteralPath $Path) {
        [System.Collections.Generic.List[string]]@(
            Get-Content -LiteralPath $Path
        )
    } else {
        [System.Collections.Generic.List[string]]::new()
    }

    $pattern = "^\s*{0}\s*=" -f [regex]::Escape($Name)
    $replacement = "$Name=$Value"
    $found = $false

    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            $lines[$index] = $replacement
            $found = $true
            break
        }
    }

    if (-not $found) {
        $lines.Add($replacement)
    }

    Set-Content -LiteralPath $Path -Value $lines -Encoding utf8
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python was not found at '$python'. Create and install the project virtual environment first."
}

foreach ($directory in @(
    (Join-Path $projectRoot "models"),
    (Join-Path $projectRoot "data\tmp"),
    (Join-Path $projectRoot "data\output")
)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot ".env.example") -Destination $envFile
}

Set-DotEnvValue -Path $envFile -Name "DEFAULT_LANGUAGE" -Value "fa"
Set-DotEnvValue -Path $envFile -Name "DEFAULT_MODEL" -Value $WhisperModel

if ($MfaCondaExecutable) {
    Set-DotEnvValue -Path $envFile -Name "MFA_CONDA_EXECUTABLE" -Value $MfaCondaExecutable
}
if ($MfaEnvironment) {
    Set-DotEnvValue -Path $envFile -Name "MFA_CONDA_ENVIRONMENT" -Value $MfaEnvironment
}

if ($Dictionary -and $AcousticModel) {
    Set-DotEnvValue -Path $envFile -Name "FA_MFA_DICTIONARY_PATH" -Value $Dictionary
    Set-DotEnvValue -Path $envFile -Name "FA_MFA_ACOUSTIC_MODEL_PATH" -Value $AcousticModel
    Write-Host "Configured the Persian MFA dictionary and acoustic model in .env."
} elseif ($Dictionary -or $AcousticModel) {
    throw "Pass both -Dictionary and -AcousticModel, or neither."
} else {
    Write-Warning "Persian Whisper transcription is prepared, but phoneme alignment is not configured yet."
    Write-Warning "Run this again with -Dictionary and -AcousticModel after creating or downloading matching Persian MFA assets."
}

if (-not $SkipWhisperDownload) {
    & (Join-Path $PSScriptRoot "Install-WhisperModel.ps1") -Model $WhisperModel -PythonExecutable $python
    if ($LASTEXITCODE -ne 0) {
        throw "Whisper model setup failed."
    }
}

Write-Host ""
Write-Host "Persian setup complete."
Write-Host "Start the server with:"
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"
