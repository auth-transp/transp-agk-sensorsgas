# Membrapor Analog Sensors: ADAM-4017+ & ADAM-4019+ Integration

This document outlines the support for analog sensors (e.g., Membrapor O2/M-1, CO, H2) using Advantech ADAM Data Acquisition Modules (**ADAM-4017+** and **ADAM-4019+**).

---

## 1. Hardware Architecture & Supported Modules

Analog gas sensors produce a **4-20mA electrical current signal**. This signal is digitized by an 8-channel Analog-to-Digital Converter (ADC) module:

* **ADAM-4017+**: 8-channel Analog Input Module supporting mV, V, and mA input signals.
* **ADAM-4019+**: 8-channel Universal Analog Input Module featuring per-channel input type configuration (4–20mA current, voltage, or thermocouple) and hardware jumper/switch configuration (e.g. ADAM-4019+-F switch settings as shown in Figure 3.15 of the Advantech ADAM-4000 manual).

### Connection Details:
- The ADAM module connects to the host computer via an **RS-485 to USB** adapter (e.g. Advantech ADAM-4561).
- Up to 8 analog sensors can be wired to a single ADAM module across Channels 0 through 7.
- RS-485 serial communication defaults to **9600 Baud Rate**, **8 Data Bits**, **1 Stop Bit**, and **No Parity (8N1)**.

> **Recommendation:** Configure the ADAM-4019+ to report **all 8 channels** in the ADAM utility software. This allows any of the 8 channel slots to be selected in the GUI Settings tab without hardware reconfiguration. The software always selects only the configured channel regardless of how many are active.

---

## 2. Communication Protocols & Module Identification

The application supports both ASCII and Modbus RTU communication protocols for ADAM-4017+ and ADAM-4019+:

### A. Advantech ASCII Protocol ([adam_driver.py](file:///e:/github/transp-agk-sensorsgas/adam_driver.py))
- **Command String**: `#01\r` (where `01` is the 2-character hex module address).
- **Response Format**: Fixed-width 7 characters per channel × 8 channels = 56-byte body, preceded by `>` and terminated by `\r` (58 bytes total):
  ```
  >       +009.73                                          \r
   ^ch0   ^ch1    ^ch2 ... ^ch7
   (7 spaces = inactive channel; '+009.73' = active channel)
  ```
  > **Important:** The ADAM-4019+ uses **space-padded fixed-width fields** for inactive channels, not signed numeric tokens. The driver parses channels using 7-character fixed-width slices, not a regex, to handle this correctly. Channels with no connected sensor return `0.0`.
- **Module Identification**:
  - Sending `$01M\r` returns the module model (`!014017+` or `!014019+`).
  - Sending `$01F\r` returns the firmware version.

### B. Modbus RTU Protocol ([adam_driver_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_driver_modbus.py))
- Reads 8 holding registers starting at address `0` (registers 40001–40008).
- Returns raw integer counts; calibration is applied by the GUI callback.
- Compatible across both ADAM-4017+ and ADAM-4019+ hardware.

---

## 3. Selecting ADAM Models in the GUI

Users can select which ADAM module model is physically connected when configuring analog sensors:

1. In the **Settings Tab**, select **Membrapor** as the sensor brand.
2. A **Model** dropdown will appear allowing selection between:
   - `ADAM-4017+` (Default)
   - `ADAM-4019+`
3. The selected model is saved in `settings.json` under `"adam_model": "ADAM-4019+"` and displayed in the Main Dashboard status info bar.

---

## 4. The AdamManager (Thread-Safe Port Sharing)

Multiple analog GUI sensors sharing a single physical RS-485 COM port use a singleton **`AdamManager`** ([adam_driver.py](file:///e:/github/transp-agk-sensorsgas/adam_driver.py)):
- Maintains one single background polling thread (`AdamThread`) per RS-485 COM port.
- Emits real-time channel arrays to all subscribed sensor panels without serial port contention or `"Access Denied"` errors.
- **Auto-Reconnect**: If the RS-485 connection is lost, `AdamThread` retries every 3 seconds. After 5 consecutive failed reads on an open port it also triggers a reconnect. Errors are surfaced via the `error_occurred` signal.

---

## 5. Calibration & Data Mapping

Analog sensors map voltage (mV) or current (mA) to gas concentration using linear interpolation:
$$\text{Concentration} = (\text{Raw\_mV} - \text{Base\_mV}) \times \left( \frac{\text{Max\_Gas\_Range}}{\text{Max\_mV} - \text{Base\_mV}} \right)$$

### Parameters in Settings:
- **Model**: `ADAM-4017+` or `ADAM-4019+`.
- **Channel**: Channel index (0 to 7).
- **Base mV**: Baseline voltage/current at 0 gas (e.g. `0.0` for 0mA, `4.0` for 4mA).
- **Max mV**: Voltage/current at full scale (e.g. `20.0` for 20mA).
- **Max Gas**: Gas PPM/PPB at full scale `Max mV`.

The calibration live display in the Settings tab shows the **Live mV**, **60-second average**, and **60-second standard deviation** of the raw channel value to assist with calibration verification.

---

## 6. Standalone Diagnostic & Debug Utilities

### ASCII Protocol Debug Tool — [adam_debug.py](file:///e:/github/transp-agk-sensorsgas/adam_debug.py)

Interactive terminal for testing ADAM-4017+/4019+ over the Advantech ASCII protocol.

```bash
python adam_debug.py
```

**Key commands:**

| Command | Description |
| :--- | :--- |
| `scan` | List all available COM ports with VID:PID and serial number |
| `open COM7` | Open serial connection to the ADAM module |
| `config` | Query module model (`$AAM`) and firmware version (`$AAF`) |
| `read` | Read all 8 channels once and display a formatted table |
| `loop [n]` | Continuous live read every `n` seconds (default 1s) — Ctrl+C to stop |
| `raw #01` | Send any raw ASCII command and print the raw response bytes |
| `addr 01` | Change the ADAM module address (default `01`) |
| `baud 9600` | Change baud rate (close/reopen port to apply) |
| `cal 1 0.0 20.0 25.0 O2%` | Apply calibration to ch1: 0–20mA → 0–25% O2 |
| `close` / `quit` | Close port / exit |

**Typical debug session:**
```
open COM7
config          ← verify module is ADAM-4019+
read            ← confirm all 8 channels appear, active channel has a value
cal 1 0.0 20.0 25.0 O2%
loop 1          ← live calibrated feed
```

### Modbus RTU Debug Tool — [adam_debug_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_debug_modbus.py)

Same interface as above but communicates over **Modbus RTU**. Raw values are integer register counts rather than floating-point mV.

```bash
python adam_debug_modbus.py
```

**Additional command:**

| Command | Description |
| :--- | :--- |
| `addr 1` | Modbus slave address (integer, default `1`) |
| `cal 1 13107 65535 25.0 O2%` | Calibration using raw int counts (4mA=13107, 20mA=65535) |

