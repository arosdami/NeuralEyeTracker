$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

python -m PyInstaller --clean --noconfirm packaging\neural_eye_tracker.spec
if ($LASTEXITCODE -ne 0) {
    throw "A portable build sikertelen."
}

Write-Host "Portable build elkészült: dist\NeuralEyeTracker.exe"
