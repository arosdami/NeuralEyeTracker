$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $knownPath = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path $knownPath) {
        $iscc = Get-Item $knownPath
    } else {
        throw "Az Inno Setup ISCC.exe nem található. Telepítse az Inno Setup 6-ot, majd futtassa újra."
    }
}

if (Test-Path ".\dist-installer") {
    Remove-Item ".\dist-installer" -Recurse -Force
}

python -m PyInstaller --clean --noconfirm `
    --distpath ".\dist-installer" `
    --workpath ".\build-installer" `
    ".\packaging\neural_eye_tracker.spec"
if ($LASTEXITCODE -ne 0) {
    throw "A PyInstaller build sikertelen."
}

& $iscc.FullName ".\packaging\NeuralEyeTracker.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Az Inno Setup build sikertelen."
}

Write-Host "Telepítő elkészült: installer\NeuralEyeTracker-Setup.exe"
