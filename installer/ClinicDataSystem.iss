#define MyAppName "ClinicDataSystem"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "ClinicDataSystem"
#define MyAppExeName "ClinicDataSystem.exe"

[Setup]
AppId={{BB2EF7C8-3FC1-4C87-A929-38A52927B146}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\MosulCharityClinic
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=admin
OutputDir=..\release
OutputBaseFilename=ClinicDataSystem-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\static\img\clinic-logo.ico
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
Name: "localserver"; Description: "تشغيل خادم العيادة المحلي تلقائياً عند تسجيل الدخول"; GroupDescription: "وضع الخادم المحلي:"

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Mosul Charity Clinic Server"""; Flags: runhidden; Tasks: localserver; Check: ShouldInstallLocalServer
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Mosul Charity Clinic Server"" dir=in action=allow program=""{app}\{#MyAppExeName}"" protocol=TCP localport=8765 enable=yes profile=any"; Flags: runhidden; Tasks: localserver; Check: ShouldInstallLocalServer
Filename: "{sys}\schtasks.exe"; Parameters: "/Create /F /SC ONLOGON /TN ""MosulCharityClinicServer"" /TR """"""{app}\{#MyAppExeName}"""" --server"""; Flags: runhidden; Tasks: localserver; Check: ShouldInstallLocalServer
Filename: "{sys}\schtasks.exe"; Parameters: "/Run /TN ""MosulCharityClinicServer"""; Flags: runhidden; Tasks: localserver; Check: ShouldInstallLocalServer
Filename: "{app}\{#MyAppExeName}"; Parameters: "--client"; Description: "تشغيل ClinicDataSystem"; Flags: nowait postinstall skipifsilent; Tasks: localserver; Check: ShouldInstallLocalServer
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل ClinicDataSystem"; Flags: nowait postinstall skipifsilent; Check: not ShouldInstallLocalServer

[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /F /TN ""MosulCharityClinicServer"""; Flags: runhidden; RunOnceId: "RemoveClinicServerTask"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Mosul Charity Clinic Server"""; Flags: runhidden; RunOnceId: "RemoveClinicFirewallRule"

[Code]
var
  DataDirPage: TInputDirWizardPage;
  ServerPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  DataDirPage := CreateInputDirPage(
    wpSelectDir,
    'مجلد بيانات العيادة',
    'اختر مكان حفظ قاعدة البيانات والمرفقات والنسخ الاحتياطية',
    'يفضّل اختيار مجلد آمن على قرص ثابت. لن يُحذف هذا المجلد عند إزالة البرنامج.',
    False,
    ''
  );
  DataDirPage.Add('');
  DataDirPage.Values[0] := ExpandConstant('{localappdata}\MosulCharityClinic\Data');
  ServerPage := CreateInputQueryPage(
    DataDirPage.ID,
    'اتصال خادم العيادة',
    'نسخة موظف أم خادم محلي؟',
    'لنسخة الموظف أدخل رابط الخادم المركزي HTTPS أو رابط الشبكة. اتركه فارغاً فقط على جهاز الخادم المحلي.'
  );
  ServerPage.Add('رابط الخادم:', False);
end;

function ShouldInstallLocalServer: Boolean;
begin
  Result := Trim(ServerPage.Values[0]) = '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ServerUrl: String;
begin
  Result := True;
  if CurPageID = ServerPage.ID then
  begin
    ServerUrl := Lowercase(Trim(ServerPage.Values[0]));
    if (ServerUrl <> '') and
       (Pos('https://', ServerUrl) <> 1) and
       (Pos('http://', ServerUrl) <> 1) then
    begin
      MsgBox('اكتب رابطاً يبدأ بـ https:// أو http://، أو اترك الحقل فارغاً للخادم المحلي.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir, JsonPath, SafePath, SafeServer, AllowLanJson: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ExpandConstant('{localappdata}\ClinicDataSystem');
    ForceDirectories(ConfigDir);
    JsonPath := ConfigDir + '\desktop.json';
    ForceDirectories(DataDirPage.Values[0]);
    SafePath := DataDirPage.Values[0];
    StringChangeEx(SafePath, '\', '/', True);
    SafeServer := Trim(ServerPage.Values[0]);
    StringChangeEx(SafeServer, '\', '/', True);
    if SafeServer = '' then AllowLanJson := 'true' else AllowLanJson := 'false';
    SaveStringToFile(JsonPath, '{"data_path":"' + SafePath + '","server_url":"' + SafeServer + '","allow_lan":' + AllowLanJson + ',"port":8765,"allow_sqlite_production":true}', False);
  end;
end;
