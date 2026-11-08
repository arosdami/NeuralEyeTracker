#define AppName "Neural Eye Tracker"
#define AppVersion "1.0.3"
#define AppPublisher "Neural Eye Lab"
#define AppExeName "NeuralEyeTracker.exe"

[Setup]
AppId={{B1E2C7B6-2A23-4B9D-B2AA-1EAE20261108}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\NeuralEyeTracker
DefaultGroupName={#AppName}
OutputDir=..\installer
OutputBaseFilename=NeuralEyeTracker-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist-installer\NeuralEyeTracker.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stimuli\*"; DestDir: "{app}\stimuli"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Asztali parancsikon létrehozása"; GroupDescription: "További ikonok:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Neural Eye Tracker indítása"; Flags: nowait postinstall skipifsilent
