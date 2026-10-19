; -----------------------------------------------------------------------------
; Aerix Language - Official Inno Setup Modern Installer Script
; Produces: AerixSetup-1.0.84.exe
; Streamlined with Tree Checkboxes, Destination Browse, and Embedded VSIX
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

; Installation Scopes: Non-admin user install by default (UAC-free)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Custom Destination Selection with Browse Button enabled
DefaultDirName={localappdata}\Programs\Aerix
DisableDirPage=no
UsePreviousAppDir=no
DirExistsWarning=no
DisableProgramGroupPage=yes

; Screen 2: License Agreement
LicenseFile=..\..\LICENSE

; Visual Branding & Modern Icons (Fluent Design)
SetupIconFile=..\assets\aerix.ico
WizardImageFile=..\assets\wizard_side.bmp
WizardSmallImageFile=..\assets\wizard_banner.bmp
WizardStyle=modern

; Output & Compression (LZMA2 Ultra64 Solid)
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

[Messages]
; Screen 1: Welcome Screen Text
WelcomeLabel1=Welcome to the Aerix Setup Wizard
WelcomeLabel2=This will install the Aerix Native Systems Programming Language v{#MyAppVersion} on your computer.%n%nAerix combines the rapid developer velocity of Python and TypeScript with the bare-metal performance, manual memory control, and zero-overhead execution of ANSI C99.%n%nIt is recommended that you close all other applications before continuing.%n%nClick Next to continue, or Cancel to exit Setup.

; Screen 8: Finished / Success Screen Text
FinishedHeadingLabel=Completing the Aerix Setup Wizard
FinishedLabel=Aerix has been successfully installed on your computer.%n%nThe 'arx' command is now available from any Command Prompt, PowerShell, or Windows Terminal window.%n%nClick Finish to exit Setup.

[Tasks]
; High-impact options organized in a clean hierarchical Tree format
Name: "envPath"; Description: "Add Aerix toolchain to User PATH (Recommended)"; Flags: checkedonce
Name: "fileAssoc"; Description: "Windows File Explorer Integration (.arx file icon, file associations & context menus)"; Flags: checkedonce
Name: "ide"; Description: "Install official extension into Code Editors:"; Flags: checkedonce
Name: "ide\vscode"; Description: "Visual Studio Code"; Flags: checkedonce
Name: "ide\antigravity"; Description: "Google Antigravity IDE"; Flags: checkedonce

[Files]
; Toolchain bin shims
Source: "arx.bat"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "..\..\arx.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\arx.py"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "..\..\arx.py"; DestDir: "{app}"; Flags: ignoreversion

; Compiler & Tools Source Tree
Source: "..\..\src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs

; Standard Library Native Runtime
Source: "..\..\stdlib\aerix_rt.h"; DestDir: "{app}\stdlib"; Flags: ignoreversion

; Official IDE Extension VSIX Bundle & 1-Click Installer
Source: "..\..\editors\vscode-aerix\aerix-1.0.84.vsix"; DestDir: "{app}\editors"; Flags: ignoreversion
Source: "..\..\editors\vscode-aerix\aerix-1.0.83.vsix"; DestDir: "{app}\editors"; Flags: ignoreversion
Source: "..\..\editors\vscode-aerix\aerix.vsix"; DestDir: "{app}\editors"; Flags: ignoreversion
Source: "..\..\editors\vscode-aerix\install_extension.bat"; DestDir: "{app}\editors"; Flags: ignoreversion

; High-DPI Multi-Size Icons
Source: "..\assets\aerix.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\aerix_file.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

; Documentation
Source: "..\..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\USER.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; -----------------------------------------------------------------------------
; 0. Environment PATH Management
; -----------------------------------------------------------------------------
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}\bin"; Tasks: envPath; Check: NeedsAddPath(ExpandConstant('{app}\bin'))

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
; 3. Explorer Context Menu Verbs
; -----------------------------------------------------------------------------
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open"; ValueType: string; ValueName: ""; ValueData: "Open with Code Editor"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """code.cmd"" ""%1"""; Tasks: fileAssoc

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: ""; ValueData: "Run with Aerix (arx run)"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" run """"%1"""""; Tasks: fileAssoc

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: ""; ValueData: "Build Executable (arx build)"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" build """"%1"""""; Tasks: fileAssoc

[Run]
; Screen 8: Finished Action Checkboxes
Filename: "{cmd}"; Parameters: "/K """"{app}\bin\arx.bat"""" doctor"; Description: "Launch Command Prompt with 'arx doctor' diagnostics"; Flags: postinstall skipifsilent nowait
Filename: "{app}\docs\GUIDE.md"; Description: "Open Aerix Master Learning Guide (GUIDE.md)"; Flags: postinstall shellexec skipifsilent unchecked

[Code]
// ----------------------------------------------------------------------------
// Win32 API Notifications & Dynamic IDE Extension Management
// ----------------------------------------------------------------------------
const
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

// Prevent duplicate PATH entries
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + UpperCase(Param) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;

// Clean PATH on uninstallation
procedure RemovePath(Param: string);
var
  OrigPath, NewPath: string;
  P: Integer;
begin
  if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    NewPath := OrigPath;
    P := Pos(';' + Param, NewPath);
    if P > 0 then
      Delete(NewPath, P, Length(';' + Param))
    else
    begin
      P := Pos(Param + ';', NewPath);
      if P > 0 then
        Delete(NewPath, P, Length(Param + ';'))
      else
      begin
        P := Pos(Param, NewPath);
        if P > 0 then
          Delete(NewPath, P, Length(Param));
      end;
    end;
    RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
  end;
end;

// Detect Visual Studio Code installation and resolve full executable path
function DetectVSCodePath(): String;
begin
  if FileExists('C:\Program Files\Microsoft VS Code\bin\code.cmd') then
    Result := 'C:\Program Files\Microsoft VS Code\bin\code.cmd'
  else if FileExists(ExpandConstant('{localappdata}\Programs\Microsoft VS Code\bin\code.cmd')) then
    Result := ExpandConstant('{localappdata}\Programs\Microsoft VS Code\bin\code.cmd')
  else if FileExists('C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd') then
    Result := 'C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd'
  else
    Result := 'code.cmd';
end;

// Detect Google Antigravity IDE installation and resolve full executable path
function DetectAntigravityPath(): String;
begin
  if FileExists('X:\Antigravity\bin\antigravity.cmd') then
    Result := 'X:\Antigravity\bin\antigravity.cmd'
  else if FileExists(ExpandConstant('{localappdata}\Programs\Antigravity\bin\antigravity.cmd')) then
    Result := ExpandConstant('{localappdata}\Programs\Antigravity\bin\antigravity.cmd')
  else if FileExists('C:\Program Files\Antigravity\bin\antigravity.cmd') then
    Result := 'C:\Program Files\Antigravity\bin\antigravity.cmd'
  else
    Result := 'antigravity.cmd';
end;

// Screen 6: Custom Ready to Install Summary Card Formatter
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := 'Destination location:' + NewLine +
       '  ' + ExpandConstant('{app}') + NewLine + NewLine +
       'Selected Tasks:' + NewLine;

  if WizardIsTaskSelected('envPath') then
    S := S + '  - Add Aerix toolchain to User PATH' + NewLine;
  if WizardIsTaskSelected('fileAssoc') then
    S := S + '  - Windows Explorer Integration (Icon, .arx association & context menus)' + NewLine;

  if WizardIsTaskSelected('ide\vscode') or WizardIsTaskSelected('ide\antigravity') then
  begin
    S := S + NewLine + 'IDE Extensions to Install:' + NewLine;
    if WizardIsTaskSelected('ide\vscode') then
      S := S + '  - Visual Studio Code (aerix.vsix)' + NewLine;
    if WizardIsTaskSelected('ide\antigravity') then
      S := S + '  - Google Antigravity IDE (aerix.vsix)' + NewLine;
  end;

  Result := S;
end;

// Install VS Code Extension via official CLI
procedure InstallVSCodeExt(VsixPath: String);
var
  ResultCode: Integer;
  CodeCmd: String;
begin
  CodeCmd := DetectVSCodePath();
  Exec('cmd.exe', '/C "' + CodeCmd + '" --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// Install Antigravity Extension via official CLI
procedure InstallAntigravityExt(VsixPath: String);
var
  ResultCode: Integer;
  AntigravityCmd: String;
begin
  AntigravityCmd := DetectAntigravityPath();
  Exec('cmd.exe', '/C "' + AntigravityCmd + '" --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// Clean extension uninstall on setup removal
procedure UninstallIDEExtensions();
var
  ResultCode: Integer;
  CodeCmd, AntigravityCmd: String;
begin
  CodeCmd := DetectVSCodePath();
  Exec('cmd.exe', '/C "' + CodeCmd + '" --uninstall-extension aerix-lang.aerix', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  AntigravityCmd := DetectAntigravityPath();
  Exec('cmd.exe', '/C "' + AntigravityCmd + '" --uninstall-extension aerix-lang.aerix', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// Post-installation step execution
procedure CurStepChanged(CurStep: TSetupStep);
var
  VsixPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 1. Notify Windows Explorer of association changes so icons render immediately
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);

    VsixPath := ExpandConstant('{app}\editors\aerix.vsix');

    // 2. Install into VS Code if checked
    if WizardIsTaskSelected('ide\vscode') then
    begin
      InstallVSCodeExt(VsixPath);
    end;

    // 3. Install into Google Antigravity IDE if checked
    if WizardIsTaskSelected('ide\antigravity') then
    begin
      InstallAntigravityExt(VsixPath);
    end;
  end;
end;

// Post-uninstallation cleanup
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemovePath(ExpandConstant('{app}\bin'));
    UninstallIDEExtensions();
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;
