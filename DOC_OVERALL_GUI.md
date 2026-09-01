# ecSense Tool: Overall Structure & GUI Operation

This document provides an overview of the architecture and user interface of the ecSense multi-sensor application.

## 1. System Architecture

The tool is built using **Python** and **PyQt6**, following a multi-threaded architecture to ensure the interface remains responsive during simultaneous data collection from multiple hardware sources.

### Core Components:
- **[main.py](file:///e:/github/transp-agk-sensorsgas/main.py)**: The entry point. Initializes the `QApplication` and launches the main window.
- **[gui_app.py](file:///e:/github/transp-agk-sensorsgas/gui_app.py)**: Contains the `MainWindow` class, `AxisControlDialog` modal, UI layout logic, tab management, plotting canvas builders, and settings persistence.
- **[data_logger.py](file:///e:/github/transp-agk-sensorsgas/data_logger.py)**: Handles writing of sensor data to CSV files, supporting "passed seconds" timestamps for easy analysis.
- **[runtime_user_data_fixed.py](file:///e:/github/transp-agk-sensorsgas/runtime_user_data_fixed.py)**: Runtime initialization hook for PyInstaller frozen builds, ensuring settings and log files (`GasSensorMonitor.log`) reside in a persistent per-user folder (`%LOCALAPPDATA%\GasSensorMonitor`).
- **`settings.json`**: A persistent configuration file that stores COM ports, sensor serial numbers, gas types, calibration parameters, plot layout modes, and manual axis range limits across sessions.

---

## 2. Graphical User Interface (GUI)

The application is organized into two primary tabs, alongside toolbar and dialog controls:

### A. Main Dashboard
The control center for live monitoring and data collection.
- **Sensor Panels**: Three independent panels to "Activate" sensors. Status labels change color dynamically (Green = Connected, Orange = Connecting, Red = Error).
- **Plotting Canvas**: A flexible Matplotlib grid that displays Gas Concentration, Temperature, and Humidity.
  - **Combined Mode**: Plots all active gas streams on a single shared graph.
  - **Separate Mode**: Stacks individual charts vertically for clearer comparison.
- **Global & Axis Controls**:
  - **Layout**: Switch between Combined and Separate plotting modes.
  - **Axis Controls Button (`AxisControlDialog`)**: Opens a modal dialog allowing users to set explicit Y-axis min/max boundaries for Sensor 1, Sensor 2, Sensor 3, Temperature, and Humidity, as well as an X-axis rolling time window (e.g. last 60 seconds).
  - **Auto-Layout Switching**: When independent gas Y-axis limits are set for individual sensors, the application automatically toggles to **Separate Gas Plots** mode to maintain distinct axes per sensor.
  - **Reset Plot View / Clear Limits**: Restores automatic scaling and clears custom axis limit entries.
  - **Start Saving Data**: Toggles CSV logging. If the target file already exists, a warning dialog is displayed before appending data.

### B. Settings Tab
The configuration hub for hardware setup.
- **Global Settings**: Select the logging frequency (1s, 5s, 10s, 30s) and browse for the destination CSV file.
- **Per-Sensor Configuration**:
  - **Brand**: Select between **ECSense** (Digital) and **Membrapor** (Analog via ADAM).
  - **Port Selection**: Manual COM port assignment or auto-discovery status.
  - **Gas Type**: Define the gas being measured (CO, H2, O2, etc.).
  - **Identify Button**: Toggles the physical LED on the sensor to visually confirm hardware mapping.
  - **Calibration (Membrapor Only)**: Input fields for Channel (0–7), Base mV, Max mV, and Max Gas range.

---

## 3. Data Logging & Persistence

Data is logged at the user-defined frequency. Each row in the CSV contains:
1. **Timestamp**: ISO-formatted date and time.
2. **Passed Seconds**: Elapsed time since the "Start Saving" button was clicked.
3. **Sensor Data**: Concentration (ppb/ppm), Temperature, and Humidity for each active sensor (NaN for inactive or error states).

Settings are automatically saved whenever a configuration is modified, ensuring settings persist across software launches and packaged `.exe` runs.

---

## 4. Standalone Executable & User Data Directory

When running the packaged executable (`dist/GasSensorMonitor.exe`):
- User configuration is maintained in `%LOCALAPPDATA%\GasSensorMonitor\settings.json`.
- Application logs are written to `%LOCALAPPDATA%\GasSensorMonitor\GasSensorMonitor.log`.
- Running **[RESET_PACKAGED_SETTINGS.bat](file:///e:/github/transp-agk-sensorsgas/RESET_PACKAGED_SETTINGS.bat)** will restore default settings from the build bundle if troubleshooting is required.
