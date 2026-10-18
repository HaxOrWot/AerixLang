; -----------------------------------------------------------------------------
; Aerix Language - Official Inno Setup Modern Installer Script
; Produces: AerixSetup-1.0.84.exe
; -----------------------------------------------------------------------------

#define MyAppName "Aerix"
#define MyAppVersion "1.0.84"
#define MyAppPublisher "HaxOrWot"
#define MyAppURL "https://github.com/HaxOrWot/AerixLang"
#define MyAppExeName "arx.bat"

[Setup]
; App Identity
AppId={{8A73E4D1-0F92-4C2E-8B51-34F6A97D1108}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

; Installation Scopes: Non-admin user install by default
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\Programs\Aerix
DisableProgramGroupPage=yes
UsePreviousAppDir=yes

; Visual Branding & Modern Icons
SetupIconFile=..\assets\aerix.ico
WizardImageFile=..\assets\wizard_side.bmp
WizardSmallImageFile=..\assets\wizard_banner.bmp
WizardStyle=modern

; Output & Compression
OutputDir=..\dist
OutputBaseFilename=AerixSetup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes

; Windows Integration
ChangesEnvironment=yes
ChangesAssociations=yes
UninstallDisplayIcon={app}\assets\aerix.ico
UninstallDisplayName={#MyAppName} Native Systems Language ({#MyAppVersion})

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "envPath"; Description: "Add Aerix to User PATH (Recommended)"; GroupDescription: "Environment Configuration:"; Flags: checkedonce
Name: "fileAssoc"; Description: "Display Aerix icon on .arx files in Windows Explorer"; GroupDescription: "File Association:"; Flags: checkedonce
Name: "contextMenu"; Description: "Add 'Run with Aerix' and 'Build Executable' to context menu"; GroupDescription: "File Association:"; Flags: checkedonce
Name: "vscodeExt"; Description: "Install extension into Visual Studio Code"; GroupDescription: "IDE Integration:"; Flags: checkedonce
Name: "antigravityExt"; Description: "Install extension into Google Antigravity IDE"; GroupDescription: "IDE Integration:"; Flags: checkedonce

[Files]
; Toolchain bin shims
Source: "..\..\arx.bat"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "..\..\arx.py"; DestDir: "{app}\bin"; Flags: ignoreversion

; Compiler & Tools Source Tree
Source: "..\..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs

; Standard Library Native Runtime
Source: "..\..\stdlib\aerix_rt.h"; DestDir: "{app}\stdlib"; Flags: ignoreversion

; Official IDE Extension VSIX
Source: "..\..\editors\vscode-aerix\aerix-1.0.84.vsix"; DestDir: "{app}\editors"; Flags: ignoreversion

; High-DPI Multi-Size Icons
Source: "..\assets\aerix.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\aerix_file.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; Documentation
Source: "..\..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\USER.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Registry]
; -----------------------------------------------------------------------------
; 1. File Association: .arx -> Aerix.SourceFile
; -----------------------------------------------------------------------------
Root: HKA; Subkey: "Software\Classes\.arx"; ValueType: string; ValueName: ""; ValueData: "Aerix.SourceFile"; Flags: uninsdeletevalue; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\.arx"; ValueType: string; ValueName: "Content Type"; ValueData: "text/plain"; Flags: uninsdeletevalue; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\.arx"; ValueType: string; ValueName: "PerceivedType"; ValueData: "text"; Flags: uninsdeletevalue; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\.arx\OpenWithProgids"; ValueType: string; ValueName: "Aerix.SourceFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileAssoc

; -----------------------------------------------------------------------------
; 2. ProgID & Explorer Custom Icon
; -----------------------------------------------------------------------------
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile"; ValueType: string; ValueName: ""; ValueData: "Aerix Source Code"; Flags: uninsdeletekey; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile"; ValueType: string; ValueName: "FriendlyTypeName"; ValueData: "Aerix Source Code (.arx)"; Flags: uninsdeletekey; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\aerix_file.ico,0"; Flags: uninsdeletekey; Tasks: fileAssoc

; -----------------------------------------------------------------------------
; 3. Explorer Context Menu Verbs (Run with Aerix, Build with Aerix)
; -----------------------------------------------------------------------------
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open"; ValueType: string; ValueName: ""; ValueData: "Open with VS Code"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """code.cmd"" ""%1"""; Tasks: fileAssoc

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: ""; ValueData: "Run with Aerix"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" run """"%1"""""; Tasks: contextMenu

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: ""; ValueData: "Build Executable (arx build)"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" build """"%1"""""; Tasks: contextMenu

[Run]
; Run arx doctor or quickstart after installation
Filename: "{cmd}"; Parameters: "/K """"{app}\bin\arx.bat"""" doctor"; Description: "Run 'arx doctor' toolchain diagnostics"; Flags: postinstall skipifsilent nowait unchecked
Filename: "{app}\docs\GUIDE.md"; Description: "Open Aerix Master Learning Guide"; Flags: postinstall shellexec skipifsilent unchecked

[Code]
// ----------------------------------------------------------------------------
// Win32 API Notifications & Environment PATH Management
// ----------------------------------------------------------------------------
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

// Flush Explorer Icon Cache
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  VsixPath: String;
  AntigravityDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 1. Notify Windows Explorer of association change so icons appear instantly
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);

    // 2. Install VS Code Extension if requested
    if WizardIsTaskSelected('vscodeExt') then
    begin
      VsixPath := ExpandConstant('{app}\editors\aerix-1.0.84.vsix');
      Exec('cmd.exe', '/C code --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;

    // 3. Install Antigravity Extension if requested
    if WizardIsTaskSelected('antigravityExt') then
    begin
      VsixPath := ExpandConstant('{app}\editors\aerix-1.0.84.vsix');
      AntigravityDir := ExpandConstant('{userdocs}\..\.antigravity-ide\extensions');
      Exec('cmd.exe', '/C antigravity --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;

// Remove from PATH on uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;
