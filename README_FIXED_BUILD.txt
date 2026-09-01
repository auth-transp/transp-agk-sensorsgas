CORRECTED SINGLE-EXE BUILD V2
=============================

WHY THE FIRST EXE DIFFERED
--------------------------
The first build changed the program's working directory to:
    %LOCALAPPDATA%\GasSensorMonitor

but did not include/copy the project's settings.json. The CMD version reads
settings.json from the project folder, so the two versions could start with
different plot, sensor, and logging settings.

The corrected build:
1. Bundles the current project settings.json.
2. Copies it to the writable per-user folder on the first launch.
3. Preserves later changes made by the client.
4. Explicitly includes the Matplotlib QtAgg backend and Matplotlib resources.

HOW TO BUILD
------------
1. Close the program.
2. Copy these files beside main.py and gui_app.py:
       BUILD_FIXED_SINGLE_EXE.bat
       GasSensorMonitor_fixed.spec
       runtime_user_data_fixed.py
       RESET_PACKAGED_SETTINGS.bat
       README_FIXED_BUILD.txt
3. Confirm the project folder contains the settings.json used by the CMD version.
4. Double-click BUILD_FIXED_SINGLE_EXE.bat.
5. The output is:
       dist\GasSensorMonitor.exe

IMPORTANT TEST ON THE SAME PC
-----------------------------
The old EXE may have left settings in %LOCALAPPDATA%\GasSensorMonitor.
The corrected runtime normally detects the old build and replaces its defaults
once. If the new EXE still shows old settings, close it, double-click:
    RESET_PACKAGED_SETTINGS.bat
and launch the new EXE again.

DIAGNOSTIC LOG
--------------
If graphs are still missing, send this file:
    %LOCALAPPDATA%\GasSensorMonitor\GasSensorMonitor.log

The final lines should contain the exact Matplotlib or application error.

DISTRIBUTION
------------
Send the newly created dist\GasSensorMonitor.exe, not the old one.
Clients do not need Python, but they still need the correct USB/serial drivers
for the connected sensor hardware.
