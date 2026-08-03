@echo off
REM Gera o executavel do X9, pronto para instalar em
REM qualquer computador Windows sem precisar de Python. Pode ser
REM clicado duas vezes direto no Explorer, ele encontra a pasta do
REM projeto sozinho.

cd /d %~dp0\..

python --version 2>nul | findstr /b "Python" >nul
if errorlevel 1 (
    echo Python nao foi encontrado de verdade no seu computador.
    echo Se apareceu algo sobre Microsoft Store, isso e so um atalho
    echo vazio, nao e o Python instalado.
    echo Baixe em https://www.python.org/downloads/ e instale
    echo marcando a caixa "Add python.exe to PATH" na primeira tela
    echo do instalador. Depois rode este arquivo de novo.
    pause
    exit /b 1
)

if not exist venv\Scripts\activate.bat (
    echo Criando ambiente virtual...
    python -m venv venv
)

if not exist venv\Scripts\activate.bat (
    echo ERRO: nao foi possivel criar o ambiente virtual em venv\
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt
pip install pyinstaller

if not exist models\yolox_nano.onnx (
    echo Baixando o modelo de deteccao...
    python scripts\download_model.py
)

echo.
echo Gerando executavel, isso pode levar alguns minutos...
pyinstaller --onefile --windowed --name X9 ^
    --add-data "models;models" ^
    --hidden-import pystray._win32 ^
    src\main.py

echo.
echo Pronto. O executavel esta em dist\X9.exe
echo Ele pede a configuracao (URL de notificacao) numa telinha na
echo primeira vez que for aberto, nao precisa editar nenhum arquivo
echo a mao.
echo.
echo Para gerar um instalador de verdade, com tela de instalacao e
echo atalho no menu iniciar, rode scripts\build_installer.bat em
echo seguida.
pause
