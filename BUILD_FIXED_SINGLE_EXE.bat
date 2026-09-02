@echo off
setlocal
cd /d "%~dp0"
title Build Gas Sensor Monitor EXE

echo ============================================================
echo   Building GasSensorMonitor.exe  (single-file)
echo   - PyQt6 and Matplotlib/QtAgg included
echo   - Current settings.json bundled as default config
echo ============================================================
echo.

:: ----------------------------------------------------------------
:: Validate required files
:: ----------------------------------------------------------------
if not exist "main.py" (
    echo ERROR: main.py not found in %CD%
    pause & exit /b 1
)
if not exist "gui_app.py" (
    echo ERROR: gui_app.py not found.
    pause & exit /b 1
)
if not exist "settings.json" (
    echo ERROR: settings.json not found.
    pause & exit /b 1
)
if not exist "GasSensorMonitor_fixed.spec" (
    echo ERROR: GasSensorMonitor_fixed.spec not found.
    pause & exit /b 1
)
if not exist "runtime_user_data_fixed.py" (
    echo ERROR: runtime_user_data_fixed.py not found.
    pause & exit /b 1
)

:: ----------------------------------------------------------------
:: Use the project virtual environment
:: ----------------------------------------------------------------
set "PY_CMD=%~dp0.venv\Scripts\python.exe"
if not exist "%PY_CMD%" (
    echo ERROR: .venv not found. Please create it first:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    pause & exit /b 1
)

echo Using: %PY_CMD%
echo.

:: ----------------------------------------------------------------
:: [1/4] Syntax check
:: ----------------------------------------------------------------
echo [1/4] Checking source files for syntax errors...
"%PY_CMD%" -m py_compile main.py gui_app.py sensor_thread.py sensor_driver.py packet_parser.py adam_driver.py adam_driver_modbus.py data_logger.py runtime_user_data_fixed.py
if errorlevel 1 (
    echo.
    echo ERROR: Syntax error found. Fix before building.
    pause & exit /b 1
)

:: ----------------------------------------------------------------
:: [2/4] Ensure PyInstaller is installed in the venv
:: ----------------------------------------------------------------
echo.
echo [2/4] Ensuring PyInstaller is available in .venv...
"%PY_CMD%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo   Installing PyInstaller into .venv...
    "%PY_CMD%" -m pip install --quiet "pyinstaller" "pyinstaller-hooks-contrib"
    if errorlevel 1 goto :failed
) else (
    echo   PyInstaller already installed.
)

:: ----------------------------------------------------------------
:: [3/4] Clean previous build output
:: ----------------------------------------------------------------
echo.
echo [3/4] Cleaning previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist\GasSensorMonitor.exe" del /q "dist\GasSensorMonitor.exe"
if exist "dist\GasSensorMonitor"     rmdir /s /q "dist\GasSensorMonitor"

:: ----------------------------------------------------------------
:: [4/4] Build
:: ----------------------------------------------------------------
echo.
echo [4/4] Building single-file executable (this takes 1-3 minutes)...
"%PY_CMD%" -m PyInstaller --noconfirm --clean "GasSensorMonitor_fixed.spec"
:: PyInstaller exits with code 1 when optional/cross-platform imports are
:: warned about (e.g. Linux/macOS modules like 'grp', 'pwd', 'termios').
:: These are harmless on Windows. Check for the actual EXE instead.

if not exist "dist\GasSensorMonitor.exe" goto :failed

echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo ============================================================
echo.
echo Output:  %CD%\dist\GasSensorMonitor.exe
echo.
echo NOTE: The first time this EXE runs it will copy the bundled
echo settings.json to %%LOCALAPPDATA%%\GasSensorMonitor\.
echo Run RESET_PACKAGED_SETTINGS.bat to restore defaults if needed.
echo.
pause
exit /b 0

:failed
echo.
echo ============================================================
echo   BUILD FAILED
echo ============================================================
echo Review the error above. Your source files were not modified.
echo.
pause
exit /b 1
