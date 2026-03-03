#define MyAppId "{{9EE3ACB7-8B7E-45A2-8A65-4EC5B45FD9A1}}"
#define MyAppName "Autoupload"
#define MyAppVersion "2026-03-04 Ver.02"
#define MyAppPublisher "JaekwonJo"
#define MyAppURL "https://github.com/JaekwonJo/autoupload"
#define MyAppExeName "Autoupload_실행.bat"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Autoupload
DefaultGroupName=Autoupload
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=Autoupload_20260304_Ver02_Setup
SetupIconFile=..\..\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\icon.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 옵션:"

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: ".git\*,.venv*\*,Lib\*,Scripts\*,logs\*,flow\logs\*,flow_downloads\*,runtime\*,flow\flow_human_profile_pw\*,flow\flow_human_profile_pw_runtime_*\*,__pycache__\*,*.pyc,*.pyo,*.pyd,*.log"

[Icons]
Name: "{group}\Autoupload"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\Autoupload"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Autoupload 실행"; Flags: nowait postinstall skipifsilent
