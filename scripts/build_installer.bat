@echo off
REM Compila o instalador final (PresenceAgentSetup.exe) a partir do
REM executavel ja gerado por build_exe.bat, usando o Inno Setup.
REM Pode ser clicado duas vezes direto no Explorer.

cd /d %~dp0\..

if not exist dist\PresenceAgent.exe (
    echo ERRO: dist\PresenceAgent.exe nao encontrado.
    echo Rode primeiro scripts\build_exe.bat
    pause
    exit /b 1
)

where ISCC >nul 2>nul
if errorlevel 1 (
    echo ERRO: Inno Setup nao encontrado no PATH.
    echo Baixe e instale em https://jrsoftware.org/isdl.php
    echo Depois de instalar, feche e abra o PowerShell de novo e
    echo rode este script outra vez.
    pause
    exit /b 1
)

ISCC scripts\PresenceAgent.iss

echo.
echo Pronto. O instalador esta em dist_installer\PresenceAgentSetup.exe
echo Esse arquivo unico ja instala o programa, cria o atalho no menu
echo iniciar e registra o desinstalador. E o que voce compartilha com
echo quem so vai usar o programa.
pause
