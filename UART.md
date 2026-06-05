# TB200B-ES1/ES4-CO-1000 UART Communication Protocol

**Device:** TB200B-ES1/ES4-CO-1000 Carbon Monoxide Gas Module  
**Source Document:** Technical Specification V1.0 20200423

---

## 1. General Communication Settings
[cite_start]The sensor module uses serial communication with the following parameters[cite: 455, 456]:

| Parameter | Value |
| :--- | :--- |
| **Baud Rate** | 9600 |
| **Data Bits** | 8 bits |
| **Stop Bit** | 1 bit |
| **Parity** | None |
| **Voltage Level** | [cite_start]3.3V UART (compatible with 5V) [cite: 56] |

**Communication Modes:**
* **Active Upload:** The sensor automatically sends data periodically.
* **Q & A (Passive):** The sensor waits for a command before sending data.
* [cite_start]**Default:** The module defaults to **Q & A mode** after power-on[cite: 458].

---

## 2. Checksum Algorithm
[cite_start]For most commands, the checksum is calculated using the following logic[cite: 486, 501, 514, 540, 563]:
1.  **Sum** the specified data bytes (typically starting from Byte 1 up to the byte immediately preceding the checksum).
2.  **Invert** the bits of the result (bitwise NOT).
3.  **Add 1** to the result.

> **Formula:** `Checksum = (~(Sum of Bytes) + 1)`

---

## 3. Mode Switching Commands

### 3.1 Switch to Active Upload Mode
[cite_start]Sets the module to automatically transmit data[cite: 461].

| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Byte 5 | Byte 6 | Byte 7 | Byte 8 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | **Retain** | **Cmd** | **Mode** | **Retain** | **Retain** | **Retain** | **Retain** | **Check** |
| `0xFF` | `0x01` | `0x78` | `0x40` | `0x00` | `0x00` | `0x00` | `0x00` | `0x47` |

### 3.2 Switch to Q & A (Passive) Mode
[cite_start]Sets the module to wait for requests[cite: 464, 465].

| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Byte 5 | Byte 6 | Byte 7 | Byte 8 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | **Retain** | **Cmd** | **Mode** | **Retain** | **Retain** | **Retain** | **Retain** | **Check** |
| `0xFF` | `0x01` | `0x78` | `0x41` | `0x00` | `0x00` | `0x00` | `0x00` | `0x46` |

---

## 4. Data Reading Commands

### 4.1 Read Gas Concentration Only
[cite_start]**Command (Hex):** `FF 01 86 00 00 00 00 00 79` [cite: 498, 499]

**Response:**
| Byte | Description | Notes |
| :--- | :--- | :--- |
| 0 | Start Bit | `0xFF` |
| 1 | Command | `0x86` |
| 2 | High Gas Conc (ug/m³) | |
| 3 | Low Gas Conc (ug/m³) | |
| 4 | Full Range High | |
| 5 | Full Range Low | |
| 6 | High Gas Conc (ppb) | |
| 7 | Low Gas Conc (ppb) | |
| 8 | Checksum | |

**Calculation:**
* [cite_start]**Gas Concentration Value:** `(High Byte * 256) + Low Byte`[cite: 502].
* *Note: Convert Hex to Decimal before applying the formula.*

### 4.2 Read Combined Data (Gas, Temp, Humidity)
[cite_start]**Command (Hex):** `FF 00 B7 00 00 00 00 00 79` [cite: 511, 512]

**Response:**
| Byte | Description | Notes |
| :--- | :--- | :--- |
| 0 | Start Bit | `0xFF` |
| 1 | Command | `0x87` |
| 2 | High Gas Conc (ug/m³) | |
| 3 | Low Gas Conc (ug/m³) | |
| 4 | Full Range High | |
| 5 | Full Range Low | |
| 6 | High Gas Conc (ppb) | |
| 7 | Low Gas Conc (ppb) | |
| 8 | Temperature High | Integer part |
| 9 | Temperature Low | Fractional part |
| 10 | Humidity High | Integer part |
| 11 | Humidity Low | Fractional part |
| 12 | Checksum | |

**Formulas:**
* [cite_start]**Temperature (°C):** `((Temp_High << 8) | Temp_Low) / 100`[cite: 516, 517].
* [cite_start]**Humidity (%RH):** `((Hum_High << 8) | Hum_Low) / 100`[cite: 518].

### 4.3 Get Temp & Humidity (Calibrated)
[cite_start]**Command:** (Implied from response context as Command 8)[cite: 536].

**Response:**
| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 |
| :--- | :--- | :--- | :--- | :--- |
| Temp High | Temp Low | Hum High | Hum Low | Checksum |

---

## 5. Module Information Commands

### 5.1 Get Sensor Info (Basic)
[cite_start]**Command (Hex):** `D1` [cite: 468]

**Response:**
| Byte | Description | Notes |
| :--- | :--- | :--- |
| 0 | Sensor Type | e.g., `0x19` for CO |
| 1 | Max Range High | |
| 2 | Max Range Low | |
| 3 | Unit | `0x02`=ppm/mg/m³, `0x04`=ppb/ug/m³ |
| 7 | Decimal & Sign | See decoding below |
| 8 | Parity Bit | |

[cite_start]**Decoding Byte 7 (Decimal & Sign)[cite: 470, 471]:**
* **Decimal Places:** Bits `[4]-[7]` (Max 3).
* **Sign:** Bits `[0]-[3]`. `0` = Positive, `1` = Negative.

### 5.2 Get Sensor Info (Extended)
[cite_start]**Command (Hex):** `FF D7 19 00 C8 02 01 00 45` (Example) [cite: 483, 484]

[cite_start]**Decoding Byte 6 (Decimal & Sign) [cite: 488-490]:**
* **Decimal Places:** `(Bit 7 << 3) | (Bit 6 << 2) | (Bit 5 << 1) | Bit 4`
* **Sign:** `(Bit 3 << 3) | (Bit 2 << 2) | (Bit 1 << 1) | Bit 0`
    * `0` = Negative inhibition.
    * `1` = Positive inhibition.

### [cite_start]5.3 Sensor Type Codes [cite: 477]
| Hex Code | Gas Type | Hex Code | Gas Type |
| :--- | :--- | :--- | :--- |
| `0x19` | CO (Carbon Monoxide) | `0x17` | HCHO |
| `0x18` | VOC | `0x1A` | Cl2 |
| `0x1B` | H2 | `0x1C` | H2S |
| `0x1D` | HCl | `0x1E` | HCN |
| `0x1F` | HF | `0xC4` | NH3 |
| `0x21` | NO2 | `0x22` | O2 |
| `0x23` | O3 | `0x24` | SO2 |

---

## 6. System Control Commands

### 6.1 Sleep Mode
**Enter Sleep:**
* [cite_start]**Command:** `AF 53 6C 65 65 70` [cite: 566-578]
* [cite_start]**Alternative:** `A1 53 6C 65 65 70 32` [cite: 607, 608]
* [cite_start]**Response:** `4F 4B` (OK) [cite: 582, 583]

**Exit Sleep:**
* [cite_start]**Command:** `AE 45 78 69 74` [cite: 591, 592]
* [cite_start]**Alternative:** `A2 45 78 69 74 32` [cite: 608]
* [cite_start]**Response:** `4F 4B` (OK) [cite: 605, 608]
* [cite_start]**Note:** Wait **5 seconds** after exiting sleep before data is available[cite: 606].

### 6.2 LED Control (Running Lights)
**Turn Off LED:**
[cite_start]`FF 01 88 00 00 00 00 00 77` [cite: 618]

**Turn On LED:**
[cite_start]`FF 01 89 00 00 00 00 00 76` [cite: 625]

**Query LED Status:**
[cite_start]`FF 01 8A 00 00 00 00 00 75` [cite: 632]
* [cite_start]**Response Byte 2:** `0x01` (On) or `0x00` (Off)[cite: 633].

### 6.3 Get Version Number
[cite_start]**Response Example:** `19 05 27 00 10 01` [cite: 550, 555-559].