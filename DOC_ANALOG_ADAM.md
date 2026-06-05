# Membrapor Analog Sensors: ADAM-4017+ Integration

This document outlines the support for analog sensors (e.g., Membrapor O2/M-1) using the Advantech ADAM-4017+ Data Acquisition Module.

## 1. Hardware Architecture

Unlike digital sensors, analog sensors produce a **4-20mA electrical signal**. This signal is digitized by an **ADAM-4017+ 8-channel Analog-to-Digital Converter (ADC)**.
- The ADAM module connects to the computer via an **RS-485 to USB** adapter.
- Multiple sensors (up to 8) can be connected to a single ADAM module.

---

## 2. Communication Protocol

The tool uses the **Advantech ASCII Protocol** to communicate with the ADAM module.
- **Command**: `#01\r` (where `01` is the module address).
- **Response**: `>+04.000+12.500+20.000...` (representing the raw mA values for all 8 channels).

### Implementation:
- **`adam_driver.py` (`Adam4017`)**: Handles the string formatting and regex-based parsing of the analog responses.

---

## 3. The AdamManager (Thread-Safe Sharing)

Because multiple sensors share a single physical COM port (the RS-485 adapter), we use a singleton **`AdamManager`**.
- It creates one single background thread (`AdamThread`) for each unique COM port.
- Individual sensor components "subscribe" to the manager.
- The manager polls the hardware once per second and broadcasts the 8-channel data to all subscribers simultaneously. This prevents port collisions and "Access Denied" errors.

---

## 4. Calibration & Data Mapping

Analog sensors require a mathematical mapping to convert current (mA) to gas concentration.

### Formula:
The tool uses a linear interpolation based on user-provided settings:
`Concentration = (Raw_mV - Base_mV) * (Max_Gas_Range / (Max_mV - Base_mV))`

### Configurable Parameters:
- **Channel**: Which of the 8 ADAM channels the sensor is wired to.
- **Base mV**: The voltage representing zero gas.
- **Max mV**: The voltage representing full scale.
- **Max Gas**: The gas concentration at the Max mV level.

---

## 5. Debugging Tools

A standalone script, **`adam_debug.py`**, is provided for testing ADAM connections without the main GUI. It allows for:
- Scanning COM ports.
- Sending raw ASCII commands.
- Visualizing live readings from all 8 channels in the terminal.
