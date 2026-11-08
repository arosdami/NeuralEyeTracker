# PyInstaller configuration for the portable Windows build.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


project_dir = Path(SPEC).resolve().parent.parent
datas = [
    (str(project_dir / "resources"), "resources"),
    (str(project_dir / "stimuli"), "stimuli"),
]
datas += collect_data_files("sklearn")


a = Analysis(
    [str(project_dir / "main.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "cv2",
        "PyQt5.sip",
        "sklearn.neural_network",
        "sklearn.preprocessing",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NeuralEyeTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
