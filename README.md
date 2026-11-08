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
- `config/` - paths, settings and release metadata
- `core/` - tracking, analysis, projects and updates
- `ui/` - PyQt5 windows and widgets
- `resources/` - read-only application resources
- `stimuli/` - read-only stimulus resources
- `packaging/` - PyInstaller and Inno Setup build files

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

The application checks the latest GitHub Release from
`arosdami/NeuralEyeTracker`. Publish the installer as a release asset whose
filename contains `Setup` and ends in `.exe`. The application can then download
and launch the installer from the Help menu or the System page.