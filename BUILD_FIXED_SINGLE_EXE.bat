@echo off
setlocal
cd /d "%~dp0"
title Build Corrected Gas Sensor Monitor EXE

echo ============================================================
echo   Building corrected GasSensorMonitor.exe
echo   - Matplotlib/QtAgg graphs included
echo   - Current settings.json included
echo ============================================================
echo.

if not exist "main.py" (
    echo ERROR: main.py was not found.
    echo Copy all files from this kit into the project folder beside main.py.
    echo.
    pause
    exit /b 1
)

if not exist "gui_app.py" (
    echo ERROR: gui_app.py was not found.
    echo.
    pause
    exit /b 1
)

if not exist "settings.json" (
    echo ERROR: settings.json was not found.
    echo The corrected EXE needs the settings file used by the CMD version.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv\Scripts\python.exe was not found.
    echo.
    pause
    exit /b 1
)

if not exist "GasSensorMonitor_fixed.spec" (
    echo ERROR: GasSensorMonitor_fixed.spec was not found.
    echo.
    pause
    exit /b 1
)

if not exist "runtime_user_data_fixed.py" (
    echo ERROR: runtime_user_data_fixed.py was not found.
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking the exact source program...
".venv\Scripts\python.exe" -m py_compile main.py gui_app.py
if errorlevel 1 goto :failed

echo.
echo [2/4] Installing/updating PyInstaller...
".venv\Scripts\python.exe" -m pip install --upgrade "pyinstaller==6.21.0" "pyinstaller-hooks-contrib"
if errorlevel 1 goto :failed

echo.
echo [3/4] Removing previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist\GasSensorMonitor.exe" del /q "dist\GasSensorMonitor.exe"

echo.
echo [4/4] Building the corrected single executable...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "GasSensorMonitor_fixed.spec"
if errorlevel 1 goto :failed

if not exist "dist\GasSensorMonitor.exe" goto :failed

echo.
echo ============================================================
echo SUCCESS
echo ============================================================
echo.
echo Corrected executable:
echo %CD%\dist\GasSensorMonitor.exe
echo.
echo IMPORTANT:
echo This corrected build installs the settings.json currently in this project
echo folder the first time it runs. Test the new EXE before sending it.
echo.
pause
exit /b 0

:failed
echo.
echo ============================================================
echo BUILD FAILED
echo ============================================================
echo Review the error shown above. Your source files were not deleted.
echo.
pause
exit /b 1
