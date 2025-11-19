@echo off
setlocal

if "%CREDENTIALS_SECRET_KEY%"=="" (
    echo CREDENTIALS_SECRET_KEY não está definida.
    echo Defina a variável antes de rodar o instalador.
    exit /B 1
)

TranscribeFlow.exe %*
