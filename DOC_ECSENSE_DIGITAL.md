# ECSense Digital Sensors: Structure & Operation

This document describes how the tool interfaces with ECSense TB200B digital gas modules.

## 1. Hardware Communication

The ECSense sensors use **FTDI-based USB-to-UART** chips. They communicate via a standard serial protocol with a baud rate of **9600**.

### Key Drivers:
- **`sensor_driver.py` (`TB200BSensor`)**: Implements the low-level hex command set.
- **`packet_parser.py`**: Handles binary data parsing and 8-bit checksum validation (`Checksum = (~(Sum of Bytes) + 1)`).

---

## 2. Operation Modes

The sensors operate in **Passive (Q&A) Mode**.
1. The tool sends a request packet (`0xFF 0x01 0x87...`).
2. The sensor responds with a 13-byte packet containing concentration, temperature, and humidity.
3. This polling occurs at 1Hz inside a dedicated background thread for each sensor.

---

## 3. Advanced Features

### A. Hardware Binding (Serial Number)
To prevent confusion when multiple sensors are plugged in, the tool reads the unique **USB Serial Number** of each FTDI chip. 
- Even if Windows reassigns a sensor from `COM4` to `COM9`, the software will recognize the Serial Number and automatically re-map it to the correct configuration.

### B. Auto-Discovery by Gas Type
If the tool cannot find a specific Serial Number, it scans all available FTDI ports and sends a `0xD1` query command. 
- The sensor responds with its built-in metadata (Gas Type, Range, Unit).
- If the response matches the "Gas Type" in settings (e.g., H2), the software binds to that port automatically.

### C. LED Identification
The tool supports a remote LED toggle feature. Clicking the **Identify** button in the GUI sends a command to the physical sensor to turn its on-board LED on or off, allowing the user to visually distinguish between multiple identical modules.

---

## 4. Concurrency Management

Each digital sensor is managed by a **`SensorThread`** (`QThread`). 
- **Resilience**: If a sensor is unplugged, the thread enters a reconnect loop, scanning for the hardware every few seconds without crashing the main application.
- **Signals**: Data is emitted back to the GUI via PyQt signals (`data_received`, `status_changed`, `sensor_info_received`).
