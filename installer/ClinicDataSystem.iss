#define MyAppName "ClinicDataSystem"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0-dev"
#endif
#define MyAppPublisher "ClinicDataSystem"
#define MyAppExeName "ClinicDataSystem.exe"

[Setup]
AppId={{BB2EF7C8-3FC1-4C87-A929-38A52927B146}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ClinicDataSystem
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=ClinicDataSystem-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\ClinicDataSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ClinicDataSystem"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ClinicDataSystem"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات إضافية:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل ClinicDataSystem"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataPage: TInputDirWizardPage;

procedure InitializeWizard;
begin
  DataPage := CreateInputDirPage(wpSelectDir,
    'مجلد بيانات العيادة',
    'اختر مكان قاعدة البيانات والنسخ الاحتياطية',
    'لن يُحذف هذا المجلد عند تحديث البرنامج أو إلغاء تثبيته. يفضّل قرصاً له نسخة احتياطية.',
    False, '');
  DataPage.Add('');
  DataPage.Values[0] := ExpandConstant('{localappdata}\ClinicDataSystem\Data');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, JsonPath, SafePath: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ExpandConstant('{localappdata}\ClinicDataSystem');
    ForceDirectories(ConfigDir);
    JsonPath := ConfigDir + '\desktop.json';
    SafePath := StringChangeEx(DataPage.Values[0], '\', '/', True);
    SaveStringToFile(JsonPath, '{"data_path":"' + SafePath + '","allow_lan":false,"port":8765}', False);
  end;
end;
