; ===========================================================================
; packaging/windows_installer.iss - Inno Setup script for MirrorZ-Hecras
; ===========================================================================
; Compile with:  ISCC packaging\windows_installer.iss   (after PyInstaller)
; Produces:      dist\MirrorZ-Hecras-Setup.exe
;
; ### TWEAK ###: bump MyAppVersion to match mirrorz/__init__.py, or pass it
; on the command line:  ISCC /DMyAppVersion=0.3.0 packaging\windows_installer.iss
; ===========================================================================

#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif
#define MyAppName "MirrorZ-Hecras"
#define MyAppPublisher "MirrorZ-Hecras contributors"
#define MyAppExeName "MirrorZ-Hecras.exe"

[Setup]
; A stable GUID keeps upgrades clean (Windows uses it to find old versions).
; Generate your own once with Inno's Tools > Generate GUID, then NEVER change it.
AppId={{6E1B2C70-5A1F-4D14-9A57-MIRRORZHEC01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename={#MyAppName}-Setup
Compression=lzma2
SolidCompression=yes
; Per-user install: no admin prompt, App-Store-style friendliness.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; \
    GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent
