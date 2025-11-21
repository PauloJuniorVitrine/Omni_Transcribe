@echo off
setlocal

REM Simple launcher to start the FastAPI GUI without relying on an external .exe

set HOST=%1
set PORT=%2
set OPT=%3
if "%HOST%"=="" set HOST=127.0.0.1
if "%PORT%"=="" set PORT=8000

if "%CREDENTIALS_SECRET_KEY%"=="" (
    echo CREDENTIALS_SECRET_KEY nao esta definida.
    echo Defina a variavel antes de rodar a GUI.
    exit /B 1
)

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
set LAUNCHER=%REPO_ROOT%\launcher_gui.py

if not exist "%LAUNCHER%" (
    echo launcher_gui.py nao encontrado em %LAUNCHER%
    exit /B 1
)

set ARGS="%LAUNCHER%" --host "%HOST%" --port "%PORT%"
if /I "%OPT%"=="--no-browser" set ARGS=%ARGS% --no-browser

echo Usando CREDENTIALS_SECRET_KEY=%CREDENTIALS_SECRET_KEY:~0,6%******
python %ARGS%
