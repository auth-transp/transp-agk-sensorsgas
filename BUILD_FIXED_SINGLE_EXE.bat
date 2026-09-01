@echo off
setlocal
cd /d "%~dp0"
title Build Corrected Gas Sensor Monitor EXE

echo ============================================================
echo   Building GasSensorMonitor.exe
echo   - PyQt6 and Matplotlib/QtAgg graphs included
echo   - Current settings.json included
echo ============================================================
echo.

if not exist "main.py" (
    echo ERROR: main.py was not found in directory: %CD%
    echo Make sure you run BUILD_FIXED_SINGLE_EXE.bat inside the project folder containing main.py.
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

set "PY_CMD="

py -c "import PyQt6" >nul 2>&1
if not errorlevel 1 set "PY_CMD=py"

if "%PY_CMD%"=="" (
    python -c "import PyQt6" >nul 2>&1
    if not errorlevel 1 set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
    echo ERROR: Could not find a Python installation with PyQt6 installed.
    echo Please ensure PyQt6 is installed by running: py -m pip install PyQt6
    echo.
    pause
    exit /b 1
)

echo Using Python command: %PY_CMD%

echo.
echo [1/4] Checking the exact source program...
%PY_CMD% -m py_compile main.py gui_app.py
if errorlevel 1 goto :failed

echo.
echo [2/4] Ensuring PyInstaller is installed...
%PY_CMD% -m pip install "pyinstaller" "pyinstaller-hooks-contrib"
if errorlevel 1 goto :failed

echo.
echo [3/4] Removing previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist\GasSensorMonitor.exe" del /q "dist\GasSensorMonitor.exe"

echo.
echo [4/4] Building single executable...
%PY_CMD% -m PyInstaller --noconfirm --clean "GasSensorMonitor_fixed.spec"
if errorlevel 1 goto :failed

if not exist "dist\GasSensorMonitor.exe" goto :failed

echo.
echo ============================================================
echo SUCCESS
echo ============================================================
echo.
echo Executable created:
echo %CD%\dist\GasSensorMonitor.exe
echo.
echo IMPORTANT:
echo This build installs the settings.json currently in this project
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
