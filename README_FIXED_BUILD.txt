GAS SENSOR MONITOR — EXE BUILD NOTES
======================================

OUTPUT
------
  dist\GasSensorMonitor.exe   (~61 MB, single file)


HOW TO BUILD
------------
Prerequisites:
  1. The project .venv must exist with all dependencies installed:
       python -m venv .venv
       .venv\Scripts\pip install -r requirements.txt
  2. settings.json must be present in the project folder.

Build:
  Double-click BUILD_FIXED_SINGLE_EXE.bat  (or run it from a terminal).
  The script uses .venv\Scripts\python.exe automatically.
  PyInstaller is installed into the venv on the first build.

Output:
  dist\GasSensorMonitor.exe


FIRST RUN BEHAVIOUR
-------------------
On the first launch the EXE copies the bundled settings.json to:
  %LOCALAPPDATA%\GasSensorMonitor\settings.json

Subsequent launches preserve any changes the user made to settings.
To restore factory defaults, run RESET_PACKAGED_SETTINGS.bat.

A diagnostic log is written to:
  %LOCALAPPDATA%\GasSensorMonitor\GasSensorMonitor.log

If graphs are missing or the app crashes silently, send this file.


TROUBLESHOOTING
---------------

PROBLEM : ModuleNotFoundError: No module named 'PIL'  (crash on launch)
CAUSE   : matplotlib 3.10+ imports PIL.Image from matplotlib.colors at
          startup. It is no longer an optional dependency.
FIX     : PIL must NOT be in the 'excludes' list in GasSensorMonitor_fixed.spec.
          The following are listed as hiddenimports in the spec:
            'PIL', 'PIL.Image', 'PIL.BmpImagePlugin', 'PIL.PngImagePlugin'
          If this error recurs after a pip upgrade, verify these entries.

PROBLEM : ModuleNotFoundError: No module named 'unittest'  (crash on launch)
CAUSE   : pyparsing.testing imports unittest at module load time, pulled in
          via matplotlib._fontconfig_pattern -> pyparsing -> pyparsing.testing.
          unittest must not be in the excludes list.
FIX     : 'unittest' and 'pytest' have been removed from excludes.
          A guard comment in GasSensorMonitor_fixed.spec explains why they
          must never be added back.

PROBLEM : Build exits with code 1 even when "Build complete!" is shown
CAUSE   : PyInstaller writes cross-platform import warnings (grp, pwd,
          termios — Linux/macOS only modules) to stderr. Some shells treat
          any stderr output as a failure exit code.
FIX     : Normal behaviour. The .bat script ignores the exit code and
          checks that dist\GasSensorMonitor.exe actually exists instead.

PROBLEM : App launches but shows different/old settings
CAUSE   : A previous build left a different settings.json in
          %LOCALAPPDATA%\GasSensorMonitor\ and the install marker
          (.corrected_build_v2_defaults_installed) already exists, so the
          new bundled defaults are not overwritten.
FIX     : Run RESET_PACKAGED_SETTINGS.bat then relaunch the new EXE.

PROBLEM : "Access Denied" or serial port errors on ADAM module
CAUSE   : Another process (or a previous app instance) has the COM port open.
FIX     : Close all other serial terminal applications. If the issue persists,
          unplug and replug the RS-485/USB adapter.

