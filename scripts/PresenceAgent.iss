; Script do Inno Setup para o Presence Agent.
; Gera um instalador Windows de verdade: tela de boas vindas, escolha
; de pasta, atalho no menu iniciar, atalho opcional na area de
; trabalho, entrada no Adicionar ou Remover Programas, e desinstalador.
;
; Como usar:
;   1. Rode scripts\build_exe.bat primeiro (gera dist\PresenceAgent.exe)
;   2. Instale o Inno Setup (gratuito): https://jrsoftware.org/isdl.php
;   3. Rode scripts\build_installer.bat, ou abra este arquivo no
;      Inno Setup Compiler e clique em Compile.

#define MyAppName "Presence Agent"
#define MyAppVersion "1.0"
#define MyAppExeName "PresenceAgent.exe"

[Setup]
AppId={{5906ED8C-4C5D-4B7F-B786-925F65299498}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\PresenceAgent
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=PresenceAgentSetup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos adicionais"
Name: "startupicon"; Description: "Iniciar automaticamente junto com o Windows"; GroupDescription: "Atalhos adicionais"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir o {#MyAppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\PresenceAgent"
