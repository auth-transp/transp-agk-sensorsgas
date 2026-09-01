@echo off
setlocal
set "APPDIR=%LOCALAPPDATA%\GasSensorMonitor"

echo This resets only the packaged EXE settings and log.
echo It does not change the project source files.
echo.

if exist "%APPDIR%\settings.json" del /q "%APPDIR%\settings.json"
if exist "%APPDIR%\.corrected_build_v2_defaults_installed" del /q "%APPDIR%\.corrected_build_v2_defaults_installed"
if exist "%APPDIR%\GasSensorMonitor.log" del /q "%APPDIR%\GasSensorMonitor.log"

echo Reset complete.
echo The corrected EXE will copy the bundled settings.json on its next launch.
echo.
pause
