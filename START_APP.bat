@echo off
color 0b
title OmniUSB Director - Bootloader

if "%~1"=="KEEP_OPEN" goto :main
cmd /k ""%~f0" KEEP_OPEN"
exit /b

:main
echo =======================================
echo Iniciando Sistema... Por favor, Espera.
echo =======================================

set MEMORY_FILE=install_path.txt

:: Adaptador de Migracion Automatica
if exist %MEMORY_FILE% (
    set /p SAVED_PATH=<%MEMORY_FILE%
) else (
    set SAVED_PATH=NONE
)

if /I not "%SAVED_PATH%"=="%CD%" (
    echo [!!!] Nueva PC o Cambio de Carpeta Detectado.
    echo [!!!] Adaptando el Motor Interno a esta nueva ubicacion...

    if exist venv (
        echo [-] Purgando entorno anterior...
        rmdir /s /q venv
    )
    if exist node_modules (
        rmdir /s /q node_modules
    )
    if exist CRASH_REPORT.txt del /q CRASH_REPORT.txt

    echo %CD%>%MEMORY_FILE%
)

echo.
echo [1/3] Chequeando Python...

:: -- Buscar Python dinamicamente --
set PYTHON=

python --version >nul 2>&1
if not errorlevel 1 ( set "PYTHON=python" & goto :python_ok )

for %%V in (313 312 311 310 39 38) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        goto :python_ok
    )
)
for %%V in (313 312 311 310 39 38) do (
    if exist "C:\Python%%V\python.exe" (
        set "PYTHON=C:\Python%%V\python.exe"
        goto :python_ok
    )
)

echo [X] Python NO encontrado. Instala Python 3.10+ desde https://python.org
pause
exit /b

:python_ok
"%PYTHON%" --version
echo [+] Python OK

echo.
echo [2/3] Construyendo Entorno...
if not exist venv (
    "%PYTHON%" -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [3/3] Chequeando Dependencias...
pip install -r requirements.txt
"%PYTHON%" auto_repair.py

echo.
echo [3.5/3] Chequeando NodeJS...
node -v >nul 2>&1
if errorlevel 1 (
    if exist "node\node.exe" (
        set "PATH=%CD%\node;%PATH%"
        echo [+] NodeJS portable activado.
    )
) else (
    echo [+] NodeJS del sistema OK.
)

echo.
echo [+] Abriendo OmniUSB...
"%PYTHON%" app.py
