# ecSense Multi-Sensor Monitor

ecSense is a Python-based multi-threaded graphical application designed for real-time monitoring, visualization, and data logging of multiple gas sensors. Developed using PyQt6 and Matplotlib, it supports a hybrid hardware setup integrating both digital and analog sensor architectures.

---

## 🚀 Key Features

*   **Real-Time Dashboard & Visualization**:
    *   Dynamic Matplotlib canvas with two plotting modes: **Combined Gas Plot** (sharing axis) or **Separate Gas Plots** (stacked vertical charts) for Gas Concentration, Temperature, and Humidity.
    *   Live-updating Sidebar display showing current values (ppm, °C, %RH) color-coded per sensor.
    *   Visual status labels indicating connection states (`Connected`, `Connecting`, `Disconnected`, `Error`).
*   **Dual Hardware Integration**:
    *   **ECSense (Digital)**: Direct interfacing with ECSense TB200B digital gas modules via UART (FTDI USB-to-serial).
    *   **Membrapor (Analog)**: Reading analog 4-20mA current outputs mapped to gas concentrations using the **Advantech ADAM-4017+** 8-channel ADC module over RS-485.
*   **Hardware Resiliency & Concurrency**:
    *   **Singleton COM Port Sharing (`AdamManager`)**: A thread-safe management module allowing multiple analog sensors to share a single serial port/adapter without packet collision or "Access Denied" errors.
    *   **FTDI Serial Number Binding**: Prevents misconfiguration due to Windows dynamically re-assigning COM ports. The software maps configuration definitions directly to the physical FTDI chip's unique serial number.
    *   **Auto-Reconnect Loop**: Independent `SensorThread` instances running in the background automatically attempt to reconnect to hardware if a cable is unplugged, ensuring the application remains crash-free.
    *   **Auto-Discovery by Gas Type**: Scans available serial ports and queries basic metadata (`0xD1` command) to auto-bind to the correct sensor based on the desired gas type configuration.
    *   **Visual LED Identification**: Remotely toggles the sensor's physical onboard running lights to identify modules in a multi-sensor array.
*   **Configurable Data Logging**:
    *   Saves data directly to CSV with high-resolution timestamps and relative "passed seconds" elapsed timers.
    *   Adjustable logging frequencies (1s, 5s, 10s, 30s) running on isolated timers to avoid GUI blockage.

---

## 🛠️ System Architecture & File Structure

```mermaid
graph TD
    Main[main.py] --> GUI[gui_app.py: MainWindow]
    GUI --> Thread1[sensor_thread.py: SensorThread 1]
    GUI --> Thread2[sensor_thread.py: SensorThread 2]
    GUI --> Thread3[sensor_thread.py: SensorThread 3]
    GUI --> Logger[data_logger.py: DataLogger]
    
    Thread1 -.-> |UART / ECSense| DigitalSensor[sensor_driver.py: TB200BSensor]
    Thread2 -.-> |UART / ECSense| DigitalSensor
    
    Thread3 -.-> |RS-485 / ASCII| AdamManager[adam_driver.py: adam_manager]
    AdamManager --> AdamADC[ADAM-4017+ ADC Module]
    
    GUI --> Settings[settings.json]
```

### File Catalog
*   [main.py](file:///e:/github/agk-examples/ecSense/main.py): Application entry point; initializes `QApplication` and styles the GUI with the PyQt Fusion style.
*   [gui_app.py](file:///e:/github/agk-examples/ecSense/gui_app.py): Core graphical interface logic including tab layout, plot builders, layout toggles, event-driven signal handlers, and settings persistence.
*   [sensor_thread.py](file:///e:/github/agk-examples/ecSense/sensor_thread.py): Implements the `QThread` background loops that query serial sensors at 1Hz and emit updates to the main GUI.
*   [sensor_driver.py](file:///e:/github/agk-examples/ecSense/sensor_driver.py): High/Low-level command set implementation for ECSense serial UART sensors.
*   [packet_parser.py](file:///e:/github/agk-examples/ecSense/packet_parser.py): Decodes binary packet frames from the UART stream and validates checks using an 8-bit checksum algorithm.
*   [adam_driver.py](file:///e:/github/agk-examples/ecSense/adam_driver.py) / [adam_driver_modbus.py](file:///e:/github/agk-examples/ecSense/adam_driver_modbus.py): Drivers for communication with Advantech ADAM-4017+ ADC modules using ASCII command protocols or Modbus.
*   [data_logger.py](file:///e:/github/agk-examples/ecSense/data_logger.py): Thread-safe file writer formatting and appending recorded readings to a CSV sheet.
*   `settings.json`: Configuration file that saves the last loaded sensor bindings (COM ports, serials, brands, gas types, plots, ADAM channel mappings, and calibrations) so that settings persist between launches.

---

## 📖 Deep-Dive Reference Documentation

To understand the communication protocols, user interface operations, and hardware specifications in detail, please refer to the following local documents:

*   📘 **[Overall GUI Architecture & Settings Guide](DOC_OVERALL_GUI.md)**: Details the design of the Main Dashboard tab, the Settings tab, data logging fields, and internal PyQt state management.
*   📘 **[ECSense Digital Sensors Guide](DOC_ECSENSE_DIGITAL.md)**: Explains the active/passive operation modes, FTDI serial binding, auto-discovery mechanisms, and LED flash controls.
*   📘 **[Analog Sensors & ADAM-4017+ Integration](DOC_ANALOG_ADAM.md)**: Covers analog 4-20mA ADC parsing, the singleton `AdamManager` architecture, and calibration formulas for mapping raw voltage measurements to gas PPM.
*   📘 **[TB200B UART Communication Protocol Reference](UART.md)**: Full register, hex command, and byte-frame reference specs for command strings (mode switching, reading, query codes, and checksum logic).

---

## ⚙️ Installation & Setup

### Prerequisites
*   Python 3.8 or higher.
*   FTDI USB-to-serial drivers (usually pre-loaded on Windows, or downloadable from the FTDI chip website).
*   RS-485 serial interface drivers (for analog module support).

### Installation Steps
1.  Clone this repository or copy the directory structure into your workspace.
2.  Install all required Python libraries via pip:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚦 How to Run & Diagnose

### Launching the Application
Execute the primary script to launch the GUI:
```bash
python main.py
```

### Running Diagnostics & Testing
If you are integrating new ADAM modules or debugging physical connections, standalone command-line testing utilities are provided:
*   **Testing Advantech ADAM ADC Modules**:
    ```bash
    python adam_debug.py
    ```
    This script lets you scan COM ports, write custom Advantech ASCII strings, and inspect the real-time voltages on all 8 ADC channels from your console.
*   **Testing UART Packet Parsing**:
    ```bash
    python debug_uart.py
    ```
