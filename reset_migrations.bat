@echo off
REM Delete all migration files from all Django apps in the project
REM This script AUTOMATICALLY DETECTS all apps with migrations/ directories
REM It only removes migration files (*.py) from migrations/ directories
REM It preserves __init__.py files to keep the directories intact

setlocal enabledelayedexpansion

REM Change to script directory (Django project root)
cd /d "%~dp0"

echo.
echo ========================================
echo Django Migrations Cleanup Script (Auto-Detect)
echo ========================================
echo.
echo Current directory: %cd%
echo.

REM Counter for deleted files
set /a DELETED=0

REM Auto-detect all directories with migrations/ subdirectory
echo Auto-detecting apps with migrations...
echo.

for /d %%D in (*) do (
    if exist "%%D\migrations" (
        set MIGRATIONS_DIR=%%D\migrations
        
        echo Cleaning migrations from: %%D
        
        REM Delete all .py files except __init__.py
        for /f %%F in ('dir /b "!MIGRATIONS_DIR!\*.py" 2^>nul') do (
            if not "%%F"=="__init__.py" (
                del /q "!MIGRATIONS_DIR!\%%F"
                set /a DELETED+=1
                echo   - Deleted: %%F
            )
        )
        
        REM Remove __pycache__ directory entirely
        if exist "!MIGRATIONS_DIR!\__pycache__" (
            echo   - Removing __pycache__ from %%D\migrations
            rmdir /s /q "!MIGRATIONS_DIR!\__pycache!"
        )
        
        REM Remove all .pyc files if any exist
        for /f %%F in ('dir /b "!MIGRATIONS_DIR!\*.pyc" 2^>nul') do (
            del /q "!MIGRATIONS_DIR!\%%F"
            set /a DELETED+=1
            echo   - Deleted: %%F
        )
        echo.
    )
)

echo ========================================
echo Summary:
echo Total migration files deleted: %DELETED%
echo ========================================
echo.

REM Ask if user wants to run makemigrations, migrate, and populate_all
set RUN_MIGRATIONS=
set /p RUN_MIGRATIONS="Do you want to run makemigrations, migrate, and populate_all? (Y/N): "
set RUN_MIGRATIONS=%RUN_MIGRATIONS: =%

if /i "%RUN_MIGRATIONS%"=="Y" (
    echo.
    echo Running makemigrations...
    python manage.py makemigrations
    
    echo.
    echo Running migrate...
    python manage.py migrate
    
    echo.
    echo Running populate_all...
    python manage.py populate_all --verbosity 2
    if !ERRORLEVEL! equ 0 (
        echo.
        echo All done!
    ) else (
        echo.
        echo Error running populate_all. Check output above.
    )
) else (
    echo.
    echo Next steps ^(run manually when ready^):
    echo 1. Run: python manage.py makemigrations
    echo 2. Run: python manage.py migrate
    echo 3. Run: python manage.py populate_all
)

echo.
