# Membrapor Analog Sensors: ADAM-4017+ Integration

This document outlines the support for analog sensors (e.g., Membrapor O2/M-1, CO, H2) using the Advantech ADAM-4017+ Data Acquisition Module.

---

## 1. Hardware Architecture

Unlike digital sensors, analog gas sensors produce a **4-20mA electrical current signal**. This signal is digitized by an **ADAM-4017+ 8-channel Analog-to-Digital Converter (ADC)**.
- The ADAM module connects to the host computer via an **RS-485 to USB** adapter.
- Up to 8 analog sensors can be wired to a single ADAM-4017+ module across Channels 0 through 7.
- RS-485 communication defaults to **9600 Baud Rate**, **8 Data Bits**, **1 Stop Bit**, and **No Parity (8N1)**.

---

## 2. Communication Protocols

The application supports two distinct protocols for interfacing with ADAM hardware:

### A. Advantech ASCII Protocol ([adam_driver.py](file:///e:/github/transp-agk-sensorsgas/adam_driver.py))
- **Command String**: `#01\r` (where `01` is the 2-character hex address of the module).
- **Response Format**: `>+04.000+12.500+20.000+00.000+00.000+00.000+00.000+00.000\r`
- **Parsing**: `Adam4017.parse_response()` extracts 8 float values (in mA or mV) using regular expressions.

### B. Modbus RTU Protocol ([adam_driver_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_driver_modbus.py))
- **Interface**: Uses Modbus RTU protocol over RS-485.
- **Implementation**: `Adam4017Modbus` queries analog input registers starting at offset `0x0000` for 8 channels.
- **Data Conversion**: Raw register integer counts are converted to engineering units (volts/millivolts/mA) based on configured channel input ranges.

---

## 3. The AdamManager (Thread-Safe Port Sharing)

Because multiple analog GUI sensors may share a single physical RS-485 COM port, direct uncoordinated serial access would lead to packet collisions and Windows `"Access Denied"` serial port errors.

To solve this, the application uses a singleton **`AdamManager`** ([adam_driver.py](file:///e:/github/transp-agk-sensorsgas/adam_driver.py)):
- It maintains one single background polling thread (`AdamThread`) for each unique COM port.
- Individual `SensorThread` instances register/subscribe to the `AdamManager`.
- The manager polls the ADAM hardware once per second and broadcasts the 8-channel reading array to all subscribers simultaneously.
- When all subscribers for a COM port are stopped, the manager automatically closes the serial port and shuts down the thread.

---

## 4. Calibration & Data Mapping

Analog sensors require mathematical scaling to convert measured voltage (mV) or current (mA) to gas PPM/PPB concentration.

### Scaling Formula:
The tool applies linear interpolation based on user configuration:
$$\text{Concentration} = (\text{Raw\_mV} - \text{Base\_mV}) \times \left( \frac{\text{Max\_Gas\_Range}}{\text{Max\_mV} - \text{Base\_mV}} \right)$$

### Configurable Parameters in Settings:
- **Channel**: Which channel (0 to 7) on the ADAM module the sensor is wired to.
- **Base mV**: The zero-gas baseline voltage (e.g. 4mA $\approx 0.8\text{V} / 800\text{mV}$).
- **Max mV**: The full-scale voltage (e.g. 20mA $\approx 4.0\text{V} / 4000\text{mV}$).
- **Max Gas**: The gas concentration equivalent at full-scale `Max mV` (e.g. 10,000 PPM for O2).

---

## 5. Standalone Diagnostic Utilities

Two standalone console scripts are provided for hardware verification outside the main GUI:

1. **[adam_debug.py](file:///e:/github/transp-agk-sensorsgas/adam_debug.py)**:
   - Scans available COM ports.
   - Tests Advantech ASCII commands (`#01\r`, `$01M\r`).
   - Displays real-time live readings for all 8 channels in terminal output.
2. **[adam_debug_modbus.py](file:///e:/github/transp-agk-sensorsgas/adam_debug_modbus.py)**:
   - Tests Modbus RTU register reading across all 8 channels.
   - Displays raw integer counts and converted voltage values per channel.
