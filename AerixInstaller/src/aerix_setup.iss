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

; Installation Scopes: Non-admin user install by default (UAC-free)
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
Name: "envPath"; Description: "Add Aerix toolchain directory to User PATH (Recommended)"; GroupDescription: "Environment Configuration:"; Flags: checkedonce
Name: "fileAssoc"; Description: "Display official supersonic Aerix icon on .arx files in Windows Explorer"; GroupDescription: "Windows Explorer Integration:"; Flags: checkedonce
Name: "contextMenu"; Description: "Add 'Run with Aerix' and 'Build Executable' to right-click context menu"; GroupDescription: "Windows Explorer Integration:"; Flags: checkedonce
Name: "vscodeExt"; Description: "Install official Aerix Language extension in Visual Studio Code"; GroupDescription: "IDE & Editor Integration:"; Flags: unchecked
Name: "antigravityExt"; Description: "Install official Aerix Language extension in Google Antigravity IDE"; GroupDescription: "IDE & Editor Integration:"; Flags: unchecked

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

; Official IDE Extension VSIX
Source: "..\..\editors\vscode-aerix\aerix-1.0.84.vsix"; DestDir: "{app}\editors"; Flags: ignoreversion

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
; 3. Explorer Context Menu Verbs (Open with Editor, Run with Aerix, Build with Aerix)
; -----------------------------------------------------------------------------
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open"; ValueType: string; ValueName: ""; ValueData: "Open with Code Editor"; Tasks: fileAssoc
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """code.cmd"" ""%1"""; Tasks: fileAssoc

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: ""; ValueData: "Run with Aerix (arx run)"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\run\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" run """"%1"""""; Tasks: contextMenu

Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: ""; ValueData: "Build Executable (arx build)"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\aerix.ico"; Tasks: contextMenu
Root: HKA; Subkey: "Software\Classes\Aerix.SourceFile\shell\build\command"; ValueType: string; ValueName: ""; ValueData: """cmd.exe"" /K """"{app}\bin\arx.bat"""" build """"%1"""""; Tasks: contextMenu

[Run]
; Run arx doctor or quickstart after installation
Filename: "{cmd}"; Parameters: "/K """"{app}\bin\arx.bat"""" doctor"; Description: "Run 'arx doctor' toolchain diagnostics"; Flags: postinstall skipifsilent nowait unchecked
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

var
  IDEPage: TInputOptionWizardPage;
  VSCodeDetected: Boolean;
  AntigravityDetected: Boolean;

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

// Detect Visual Studio Code installation
function DetectVSCode(): Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Microsoft VS Code\bin\code.cmd')) or
            FileExists('C:\Program Files\Microsoft VS Code\bin\code.cmd') or
            FileExists('C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd') or
            DirExists(ExpandConstant('{userdocs}\..\.vscode'));
end;

// Detect Google Antigravity IDE installation
function DetectAntigravity(): Boolean;
begin
  Result := FileExists('X:\Antigravity\bin\antigravity.cmd') or
            FileExists(ExpandConstant('{localappdata}\Programs\Antigravity\bin\antigravity.cmd')) or
            DirExists(ExpandConstant('{userdocs}\..\.antigravity-ide'));
end;

// Resolve path to code.cmd
function GetVSCodeCmd(): String;
begin
  if FileExists(ExpandConstant('{localappdata}\Programs\Microsoft VS Code\bin\code.cmd')) then
    Result := ExpandConstant('{localappdata}\Programs\Microsoft VS Code\bin\code.cmd')
  else if FileExists('C:\Program Files\Microsoft VS Code\bin\code.cmd') then
    Result := 'C:\Program Files\Microsoft VS Code\bin\code.cmd'
  else if FileExists('C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd') then
    Result := 'C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd'
  else
    Result := 'code.cmd';
end;

// Resolve path to antigravity.cmd
function GetAntigravityCmd(): String;
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

// Custom Wizard Page Initialization
procedure InitializeWizard();
var
  VSCodeText, AntigravityText: String;
begin
  VSCodeDetected := DetectVSCode();
  AntigravityDetected := DetectAntigravity();

  VSCodeText := 'Install official Aerix Language extension in Visual Studio Code';
  if VSCodeDetected then
    VSCodeText := VSCodeText + ' (Detected on this system)';

  AntigravityText := 'Install official Aerix Language extension in Google Antigravity IDE';
  if AntigravityDetected then
    AntigravityText := AntigravityText + ' (Detected on this system)';

  // Create dedicated interactive option page directly after Select Tasks page
  IDEPage := CreateInputOptionPage(wpSelectTasks,
    'IDE & Editor Integration',
    'Choose code editors to configure with Aerix language intelligence',
    'Aerix provides rich syntax highlighting, snippets, and Language Server (LSP) diagnostics.' + #13#10#13#10 +
    'The installer has detected your installed developer environments. Check the options below if you would like Setup to configure them automatically:',
    False, False);

  IDEPage.Add(VSCodeText);
  IDEPage.Add(AntigravityText);

  // If detected, pre-check so the option is conveniently offered, or let user prompt/toggle
  IDEPage.Values[0] := VSCodeDetected or WizardIsTaskSelected('vscodeExt');
  IDEPage.Values[1] := AntigravityDetected or WizardIsTaskSelected('antigravityExt');
end;

// Install VS Code Extension with CLI execution and direct filesystem fallback
procedure InstallVSCodeExt(VsixPath: String);
var
  ResultCode: Integer;
  CodeCmd: String;
begin
  CodeCmd := GetVSCodeCmd();
  // 1. Try CLI
  if not Exec('cmd.exe', '/C "' + CodeCmd + '" --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    // 2. Direct unpack fallback via PowerShell Expand-Archive
    Exec('powershell.exe', '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ' +
      '"$dest = Join-Path $env:USERPROFILE ''.vscode\extensions\aerix-lang.aerix-1.0.84''; ' +
      'if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }; ' +
      '$tmp = Join-Path $env:TEMP ''aerix_vsix_tmp''; ' +
      'if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }; ' +
      'Expand-Archive -Path ''' + VsixPath + ''' -DestinationPath $tmp -Force; ' +
      'Move-Item -Path (Join-Path $tmp ''extension'') -Destination $dest -Force; ' +
      'Remove-Item -Recurse -Force $tmp"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Install Antigravity Extension with CLI execution and direct filesystem fallback
procedure InstallAntigravityExt(VsixPath: String);
var
  ResultCode: Integer;
  AntigravityCmd: String;
begin
  AntigravityCmd := GetAntigravityCmd();
  // 1. Try CLI
  if not Exec('cmd.exe', '/C "' + AntigravityCmd + '" --install-extension "' + VsixPath + '" --force', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    // 2. Direct unpack fallback via PowerShell Expand-Archive
    Exec('powershell.exe', '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command ' +
      '"$dest = Join-Path $env:USERPROFILE ''.antigravity-ide\extensions\aerix-lang.aerix-1.0.84''; ' +
      'if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }; ' +
      '$tmp = Join-Path $env:TEMP ''aerix_anti_tmp''; ' +
      'if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }; ' +
      'Expand-Archive -Path ''' + VsixPath + ''' -DestinationPath $tmp -Force; ' +
      'Move-Item -Path (Join-Path $tmp ''extension'') -Destination $dest -Force; ' +
      'Remove-Item -Recurse -Force $tmp"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Post-installation step execution
procedure CurStepChanged(CurStep: TSetupStep);
var
  VsixPath: String;
  ShouldInstallVSCode: Boolean;
  ShouldInstallAntigravity: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    // 1. Notify Windows Explorer of association changes so icons render immediately
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);

    VsixPath := ExpandConstant('{app}\editors\aerix-1.0.84.vsix');

    // 2. Determine if user prompted / opted into VS Code extension install
    ShouldInstallVSCode := False;
    if Assigned(IDEPage) then
      ShouldInstallVSCode := IDEPage.Values[0]
    else
      ShouldInstallVSCode := WizardIsTaskSelected('vscodeExt');

    if ShouldInstallVSCode then
    begin
      InstallVSCodeExt(VsixPath);
    end;

    // 3. Determine if user prompted / opted into Antigravity IDE extension install
    ShouldInstallAntigravity := False;
    if Assigned(IDEPage) then
      ShouldInstallAntigravity := IDEPage.Values[1]
    else
      ShouldInstallAntigravity := WizardIsTaskSelected('antigravityExt');

    if ShouldInstallAntigravity then
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
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
  end;
end;
