#define MyAppId "{{9EE3ACB7-8B7E-45A2-8A65-4EC5B45FD9A1}}"
#define MyAppName "Flow Veo 자동화 봇"
#define MyAppVersion "2026-03-03 Ver.01"
#define MyAppPublisher "JaekwonJo"
#define MyAppURL "https://github.com/JaekwonJo/autoupload"
#define MyAppExeName "FlowVeo_실행.bat"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\FlowVeoAutoupload
DefaultGroupName=Flow Veo 자동화 봇
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=FlowVeo_20260303_Ver01_Setup
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
Name: "desktopicon"; Description: "바탕화면 바로가기 만들기"; GroupDescription: "추가 옵션:"; Flags: unchecked

[Files]
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: ".git\*,.venv*\*,Lib\*,Scripts\*,logs\*,flow\logs\*,flow_downloads\*,runtime\*,flow\flow_human_profile_pw\*,flow\flow_human_profile_pw_runtime_*\*,__pycache__\*,*.pyc,*.pyo,*.pyd,*.log"

[Icons]
Name: "{group}\Flow Veo 자동화 봇"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\Flow Veo 자동화 봇"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Flow Veo 자동화 봇 실행"; Flags: nowait postinstall skipifsilent
