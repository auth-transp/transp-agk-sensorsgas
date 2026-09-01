# Membrapor Analog Sensors: ADAM-4017+ & ADAM-4019+ Integration

This document outlines the support for analog sensors (e.g., Membrapor O2/M-1, CO, H2) using Advantech ADAM Data Acquisition Modules (**ADAM-4017+** and **ADAM-4019+**).

---

## 1. Hardware Architecture & Supported Modules

Analog gas sensors produce a **4-20mA electrical current signal**. This signal is digitized by an 8-channel Analog-to-Digital Converter (ADC) module:

* **ADAM-4017+**: 8-channel Analog Input Module supporting mV, V, and mA input signals.
* **ADAM-4019+**: 8-channel Universal Analog Input Module featuring per-channel input type configuration (4–20mA current, voltage, or thermocouple) and hardware jumper/switch configuration (e.g. ADAM-4019+-F switch settings as shown in Figure 3.15 of the Advantech ADAM-4000 manual).

### Connection Details:
- The ADAM module connects to the host computer via an **RS-485 to USB** adapter.
- Up to 8 analog sensors can be wired to a single ADAM module across Channels 0 through 7.
- RS-485 serial communication defaults to **9600 Baud Rate**, **8 Data Bits**, **1 Stop Bit**, and **No Parity (8N1)**.

---

## 2. Communication Protocols & Module Identification

The application supports both ASCII and Modbus RTU communication protocols for ADAM-4017+ and ADAM-4019+:

### A. Advantech ASCII Protocol ([adam_driver.py](file:///e:/github/transp-agk-sensorsgas/adam_driver.py))
- **Command String**: `#01\r` (where `01` is the 2-character hex module address).
- **Response Format**: `>+04.000+12.500+20.000+00.000+00.000+00.000+00.000+00.000\r` (Shared format between 4017+ and 4019+).
- **Module Identification**:
  - Sending `$01M\r` returns the module model (`!014017+` or `!014019+`).
  - Sending `$01F\r` returns the firmware version.

### B. Modbus RTU Protocol ([adam_driver_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_driver_modbus.py))
- Reads 8 holding registers starting at address `0` (registers 40001–40008).
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

---

## 5. Calibration & Data Mapping

Analog sensors map voltage (mV) or current (mA) to gas concentration using linear interpolation:
$$\text{Concentration} = (\text{Raw\_mV} - \text{Base\_mV}) \times \left( \frac{\text{Max\_Gas\_Range}}{\text{Max\_mV} - \text{Base\_mV}} \right)$$

### Parameters in Settings:
- **Model**: `ADAM-4017+` or `ADAM-4019+`.
- **Channel**: Channel index (0 to 7).
- **Base mV**: Baseline voltage at 0 gas.
- **Max mV**: Voltage at full scale.
- **Max Gas**: Gas PPM/PPB at full scale `Max mV`.

---

## 6. Standalone Diagnostic Utilities

- **[adam_debug.py](file:///e:/github/transp-agk-sensorsgas/adam_debug.py)**: ASCII protocol CLI debugger with `$AAM` module identification.
- **[adam_debug_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_debug_modbus.py)**: Modbus RTU protocol CLI debugger for 4017+/4019+.
