@echo off
REM Presence Agent - instalador automatico
REM
REM Clique duas vezes neste arquivo. Ele confere se o Python esta
REM instalado, prepara tudo, gera o executavel e, se o Inno Setup
REM tambem estiver instalado, gera o instalador completo
REM (PresenceAgentSetup.exe) no final.
REM
REM Precisa rodar so uma vez, na maquina onde voce vai gerar o
REM programa para distribuir. Quem so vai usar o resultado nao
REM precisa deste arquivo.

cd /d %~dp0
setlocal

echo ============================================
echo   Presence Agent - preparando tudo
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 goto :python_ausente

python --version 2>nul | findstr /b "Python" >nul
if errorlevel 1 goto :python_ausente

goto :python_ok

:python_ausente
echo Python nao foi encontrado de verdade no seu computador.
echo.
echo Se apareceu uma mensagem falando em Microsoft Store, isso e so
echo um atalho vazio que o Windows coloca no lugar do Python, nao e
echo o Python de verdade instalado.
echo.
echo Resolva assim:
echo   1. Abra Configuracoes do Windows, va em Aplicativos, depois
echo      Configuracoes avancadas de aplicativos, depois Aliases de
echo      execucao de aplicativo. Desative python.exe e python3.exe.
echo   2. Baixe o Python em https://www.python.org/downloads/ e
echo      instale marcando a caixa "Add python.exe to PATH" na
echo      primeira tela do instalador.
echo   3. Feche esta janela e clique de novo neste arquivo.
pause
exit /b 1

:python_ok
echo Python encontrado, gerando o executavel...
echo.
call scripts\build_exe.bat
if errorlevel 1 (
    echo.
    echo Alguma coisa falhou ao gerar o executavel. Veja a mensagem
    echo de erro acima.
    pause
    exit /b 1
)

where ISCC >nul 2>nul
if errorlevel 1 (
    echo.
    echo ============================================
    echo   Pronto ate aqui
    echo ============================================
    echo O executavel esta em dist\PresenceAgent.exe
    echo.
    echo Para gerar tambem um instalador completo, com tela de
    echo instalacao e atalho no menu iniciar, instale o Inno Setup
    echo gratuito em https://jrsoftware.org/isdl.php e clique de
    echo novo neste arquivo depois.
    pause
    exit /b 0
)

echo.
echo Inno Setup encontrado, gerando o instalador final...
echo.
call scripts\build_installer.bat

echo.
echo ============================================
echo   Tudo pronto
echo ============================================
echo O instalador final esta em dist_installer\PresenceAgentSetup.exe
echo Esse e o arquivo que voce compartilha com quem so vai usar o
echo programa.
pause
