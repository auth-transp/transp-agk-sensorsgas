# ECSense Digital Sensors: Structure & Operation

This document describes how the ecSense tool interfaces with ECSense TB200B digital gas modules.

---

## 1. Hardware Communication & Driver Architecture

ECSense digital sensors utilize onboard **FTDI USB-to-UART** interface chips. They communicate via standard asynchronous serial protocols:
- **Baud Rate**: 9600
- **Data Bits**: 8
- **Stop Bit**: 1
- **Parity**: None (8N1)
- **Voltage Level**: 3.3V UART (5V tolerant)

### Core Driver Components:
- **[sensor_driver.py](file:///e:/github/transp-agk-sensorsgas/sensor_driver.py) (`TB200BSensor`)**: Implements low-level hex command construction and serial read/write transactions.
- **[packet_parser.py](file:///e:/github/transp-agk-sensorsgas/packet_parser.py)**: Decodes 13-byte binary response frames, extracts gas concentration, temperature, and humidity, and validates packets using an 8-bit checksum:
  $$\text{Checksum} = (\sim \text{Sum of Bytes}) + 1$$

---

## 2. Operation Modes

The sensors operate in **Passive (Q & A) Mode**:
1. The `SensorThread` sends a 9-byte request frame (`0xFF 0x01 0x87 0x00 0x00 0x00 0x00 0x00 0x78` or `0x79`).
2. The sensor returns a 13-byte payload containing gas concentration (ug/m³ and ppb), temperature (°C), and humidity (%RH).
3. Polling takes place at 1Hz inside a dedicated background `SensorThread` instance per digital sensor.

---

## 3. Hardware Management & Resiliency

### A. Hardware Binding (FTDI Serial Number)
To prevent sensor misconfiguration when multiple USB serial devices are connected, the tool queries the unique **USB Serial Number** of each FTDI chip (e.g. `A5069RR4A`).
- If Windows dynamically reassigns a device from `COM4` to `COM9`, the application automatically matches the physical chip's serial number back to its configured gas stream in `settings.json`.

### B. Auto-Discovery by Gas Type
If a configured serial number is missing or changed, the application performs an auto-discovery routine:
1. It scans all available COM ports with FTDI identifiers.
2. It sends a basic metadata query command (`0xD1`).
3. The sensor returns its internal metadata (Gas Type code, unit, range).
4. If the gas type matches the slot configuration (e.g., CO or H2), the port is bound automatically.

### C. Visual LED Identification
Clicking the **Identify** button in the settings UI sends hex commands (`0xFF 0x01 0x89...` / `0xFF 0x01 0x88...`) to toggle the physical onboard LED running light on the module, allowing operators to visually confirm sensor location in multi-module setups.

---

## 4. Concurrency & Signal Flow

- Each active digital sensor runs inside its own **`SensorThread`** (`QThread`).
- **Auto-Reconnect**: If a USB cable is disconnected during operation, the thread catches the error, sets status to `Connecting`, and enters a non-blocking recovery loop without crashing the main application GUI.
- Data updates are emitted via PyQt signals (`data_received`, `status_changed`, `sensor_info_received`) directly to the main GUI plotting engine and CSV logger.

---

## 5. Standalone Debug Utility — [debug_uart.py](file:///e:/github/transp-agk-sensorsgas/debug_uart.py)

A non-interactive command-line tool for verifying raw UART communication with a TB200B sensor before using the GUI.

```bash
python debug_uart.py --port COM3 --baud 9600
```

**Arguments:**

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--port` | `COM7` | COM port the sensor is connected to |
| `--baud` | `9600` | Baud rate |

**What it tests (in sequence):**

1. **Set Passive Mode** (`0x78 0x41`) — switches the sensor out of active upload mode.
2. **Read Gas Only** (`0x86`) — 9-byte response; validates checksum.
3. **Read Combined** (`0xB7`, checksum `0x49`) — 13-byte gas+temp+hum response, calculated checksum variant.
4. **Read Combined** (`0xB7`, checksum `0x79`) — alternate checksum variant from the spec document.
5. **Read Combined Variant** (`0x87`) — the command variant used by the main application.

For each test it prints the sent bytes in hex, the received bytes in hex, and whether the checksum is valid. This is the fastest way to confirm the sensor is alive and which command variant it responds to correctly.

**Example output:**
```
[Read Combined Variant (0x87)] Sending: ['0xff', '0x01', '0x87', ...]
[Read Combined Variant (0x87)] Received (13 bytes): ['0xff', '0x87', '0x00', '0x0a', ...]
[Read Combined Variant (0x87)] Checksum Valid: True (Calc: 0x78, Recv: 0x78)
```

