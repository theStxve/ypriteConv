; Inno Setup script for ypriteConvert
; Build: iscc /DAppVersion=1.2.3 installer\ypriteConvert.iss   (run from the project root)
; Needs: dist\ypriteConvert\ (PyInstaller) and bin\ffmpeg.exe (+ ffprobe.exe)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "ypriteConvert"
#define AppExe "ypriteConvert.exe"
#define AppPublisher "theStxve"
#define AppURL "https://github.com/theStxve/ypriteConv"

[Setup]
; Never change AppId - it ties updates to the existing installation
AppId={{6E2B8F41-3C9A-4D7E-9B15-2A7F0C8D4E93}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}
; Per-user install by default -> no admin prompt, silent auto-updates just work
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
SetupIconFile=..\assets\icon.ico
WizardSmallImageFile=..\assets\wizard-small.bmp
WizardStyle=modern
OutputDir=..\Output
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no
ChangesAssociations=yes
SetupMutex={#AppName}SetupMutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
english.ContextMenu=Add "Convert with ypriteConvert" to the Explorer right-click menu
german.ContextMenu=„Mit ypriteConvert konvertieren“ zum Explorer-Rechtsklickmenü hinzufügen
english.ContextMenuText=Convert with ypriteConvert
german.ContextMenuText=Mit ypriteConvert konvertieren

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "contextmenu"; Description: "{cm:ContextMenu}"; GroupDescription: "Explorer:"

[InstallDelete]
; Remove files of the previous version so stale DLLs never linger
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\ypriteConvert\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\bin\ffmpeg.exe"; DestDir: "{app}\bin"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Right-click on any file / folder. Explorer starts one process per file;
; the app forwards them to the already open window.
Root: HKA; Subkey: "Software\Classes\*\shell\ypriteConvert"; ValueType: string; ValueName: ""; ValueData: "{cm:ContextMenuText}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\*\shell\ypriteConvert"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\*\shell\ypriteConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\Directory\shell\ypriteConvert"; ValueType: string; ValueName: ""; ValueData: "{cm:ContextMenuText}"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\Directory\shell\ypriteConvert"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\Directory\shell\ypriteConvert\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: contextmenu
; "Open with" list
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Flags: uninsdeletekey

[Run]
; Normal install: offer to launch. Silent auto-update: always relaunch.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\bin"
