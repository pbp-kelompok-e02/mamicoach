@echo off
set VENV_DIR=venv
set REQ_FILE=requirements.txt


:: Check if venv exists and has activate.bat
set VENV_OK=0
if not exist "%VENV_DIR%" (
    set VENV_OK=1
) else if not exist "%VENV_DIR%\Scripts\activate.bat" (
    set VENV_OK=1
)

if %VENV_OK%==1 (
    echo Creating Windows-compatible virtual environment...
    rmdir /s /q "%VENV_DIR%" 2>nul
    python -m venv %VENV_DIR%
) else (
    echo Virtual environment already exists and is Windows-compatible.
)


:: Try to activate venv (check both possible locations)
set ACTIVATE_FOUND=
if exist "%VENV_DIR%\Scripts\activate.bat" (
    set ACTIVATE_FOUND=%VENV_DIR%\Scripts\activate.bat
) else if exist "%VENV_DIR%\bin\activate.bat" (
    set ACTIVATE_FOUND=%VENV_DIR%\bin\activate.bat
)

if defined ACTIVATE_FOUND (
    call "%ACTIVATE_FOUND%"
) else (
    echo ERROR: Cannot find activate.bat in Scripts or bin folder.
    echo Please check your virtual environment.
    exit /b 1
)

:: Install requirements
if exist "%REQ_FILE%" (
    echo Installing dependencies...
    python -m pip install -U pip
    python -m pip install -r %REQ_FILE%
) else (
    echo requirements.txt not found, skipping installation.
)

:: Run Django server if manage.py exists
if exist "manage.py" (
    echo Preparing to run Django server...
    python manage.py migrate
    echo Running Django server...
    python manage.py runserver
) else (
    echo Setup complete. To activate later, run:
    echo     %VENV_DIR%\Scripts\activate
)
