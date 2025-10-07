@echo off
set VENV_DIR=venv
set REQ_FILE=requirements.txt

:: Check if venv exists
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
) else (
    echo Virtual environment already exists.
)

:: Activate venv
call %VENV_DIR%\Scripts\activate.bat

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
    echo Running Django server...
    python manage.py runserver
) else (
    echo Setup complete. To activate later, run:
    echo     %VENV_DIR%\Scripts\activate
)
