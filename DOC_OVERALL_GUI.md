# ecSense Tool: Overall Structure & GUI Operation

This document provides an overview of the architecture and user interface of the ecSense multi-sensor application.

## 1. System Architecture

The tool is built using **Python** and **PyQt6**, following a multi-threaded architecture to ensure the interface remains responsive during simultaneous data collection from multiple hardware sources.

### Core Components:
- **`main.py`**: The entry point. Initializes the `QApplication` and launches the main window.
- **`gui_app.py`**: Contains the `MainWindow` class and all UI logic, including tab management, plotting, and settings persistence.
- **`data_logger.py`**: Handles writing of sensor data to CSV files, supporting "passed seconds" timestamps for easy analysis.
- **`settings.json`**: A persistent configuration file that stores COM ports, sensor serial numbers, gas types, and calibration parameters across sessions.

---

## 2. Graphical User Interface (GUI)

The application is organized into two primary tabs:

### A. Main Dashboard
The control center for live monitoring and data collection.
- **Sensor Panels**: Three independent panels to "Activate" sensors. Status labels change color dynamically (Green = Connected, Orange = Connecting, Red = Error).
- **Plotting Canvas**: A flexible Matplotlib grid that displays Gas Concentration, Temperature, and Humidity.
  - **Combined Mode**: Plots all active gas streams on a single shared graph.
  - **Separate Mode**: Stacks individual charts vertically for clearer comparison.
- **Global Controls**:
  - **Layout**: Switch between Combined and Separate plotting modes.
  - **Start Saving Data**: Toggles CSV logging. If the file exists, a warning is shown before appending.

### B. Settings Tab
The configuration hub for hardware setup.
- **Global Settings**: Select the logging frequency (1s, 5s, 10s, 30s) and browse for the destination CSV file.
- **Per-Sensor Configuration**:
  - **Brand**: Select between **ECSense** (Digital) and **Membrapor** (Analog via ADAM).
  - **Port Selection**: Manual COM port assignment or auto-discovery status.
  - **Gas Type**: Define the gas being measured (CO, H2, O2, etc.).
  - **Identify Button**: Toggles the physical LED on the sensor to visually confirm hardware mapping.
  - **Calibration (Membrapor Only)**: Input fields for Channel, Base mV, Max mV, and Max Gas range.

---

## 3. Data Logging & Persistence

Data is logged at the user-defined frequency. Each row in the CSV contains:
1. **Timestamp**: ISO formatted date and time.
2. **Passed Seconds**: Elapsed time since the "Start Saving" button was clicked.
3. **Sensor Data**: Concentration (ppb/ppm), Temperature, and Humidity for each active sensor (NaN for inactive or error states).

Settings are automatically saved whenever a configuration is changed, ensuring the tool is ready to use immediately upon the next launch.
