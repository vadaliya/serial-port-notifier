#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#ifndef ExecutablePath
#define ExecutablePath "dist\SerialPortNotifier.exe"
#endif
#ifndef OutputName
#define OutputName "SerialPortNotifier-setup"
#endif

[Setup]
AppName=Serial Port Notifier
AppVersion={#AppVersion}
AppPublisher=Google LLC
AppPublisherURL=https://github.com/vadaliya/serial-port-notifier
AppSupportURL=https://github.com/vadaliya/serial-port-notifier/issues
AppUpdatesURL=https://github.com/vadaliya/serial-port-notifier/releases
DefaultDirName={autopf}\SerialPortNotifier
DefaultGroupName=Serial Port Notifier
UninstallDisplayIcon={app}\SerialPortNotifier.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename={#OutputName}
SetupIconFile=assets\logo.ico
; Dual-mode setup: lets user choose "Only for me" (no admin rights) or "All users" (requires admin)
PrivilegesRequiredOverridesAllowed=dialog

[Files]
Source: "{#ExecutablePath}"; DestDir: "{app}"; DestName: "SerialPortNotifier.exe"; Flags: ignoreversion
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\Serial Port Notifier"; Filename: "{app}\SerialPortNotifier.exe"
Name: "{autodesktop}\Serial Port Notifier"; Filename: "{app}\SerialPortNotifier.exe"

[Run]
Filename: "{app}\SerialPortNotifier.exe"; Description: "Launch Serial Port Notifier"; Flags: nowait postinstall skipifsilent
