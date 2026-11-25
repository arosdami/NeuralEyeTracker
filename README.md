# Neural Eye Tracker

Professional pupil and gaze tracking application for research and clinical workflows.

## Features

- Real-time pupil detection with multi-stage pipeline
- Neural network gaze prediction (MLP with 4 layers)
- 3D eye model with OpenGL
- 9-point calibration system
- ROI selection
- Real-time heatmap
- Professional UI with dark theme

## Project layout

- `main.py` - application entry point
- `web/` - local React/Vite clinical workspace and Python tracker bridge
- `config/` - paths, settings and release metadata
- `core/` - tracking, analysis, projects and updates
- `ui/` - PyQt5 windows and widgets
- `resources/` - read-only application resources
- `stimuli/` - read-only stimulus resources
- `packaging/` - PyInstaller and Inno Setup build files

## Local React clinical workspace

The clinical workspace runs locally through React/Vite and connects to the
real camera-processing core through `web/backend_server.py`. It is not a
dummy-data preview: the camera frame, pupil geometry, confidence and
calibration state come from the Python tracker.

```powershell
Set-Location .\web
.\indit-klinikai-munkater.bat
```

The script starts the Python API on `http://127.0.0.1:8765` and the React
interface on `http://127.0.0.1:5173/`. Click **Rögzítés** to open the camera,
then **Kalibrálás** to collect the configured gaze samples. If no camera is
available, the interface reports the real error instead of displaying
generated measurements.

## Runtime data

The application stores user accounts, reports, calibration models and settings in
`%LOCALAPPDATA%\NeuralEyeTracker` on Windows. Project files and stimuli remain
read-only application resources, so the installed application does not need
write access to `Program Files`.

## Portable build

Install the development dependencies and build the application folder:

```powershell
python -m pip install -r requirements-dev.txt
.\packaging\build-portable.ps1
```

The executable is created at
`dist\NeuralEyeTracker.exe`. It can be copied to another Windows machine without
installing Python.

## Windows installer

Install Inno Setup 6, then run:

```powershell
python -m pip install -r requirements-dev.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\packaging\build-installer.ps1
```

The installer is created at `installer\NeuralEyeTracker-Setup.exe`.

## Updates

Updates are read from the GitHub Releases of `arosdami/NeuralEyeTracker`.
Make this repository public and publish each installer as a Release asset
whose filename contains `Setup` and ends in `.exe`. The application can then
download and launch the installer from the Help menu or the System page.