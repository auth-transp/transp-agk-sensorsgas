# TB200B-ES1/ES4-CO-1000 UART Communication Protocol

**Device:** TB200B-ES1/ES4-CO-1000 Carbon Monoxide Gas Module  
**Source Document:** Technical Specification V1.0  
**Implementation:** [sensor_driver.py](file:///e:/github/transp-agk-sensorsgas/sensor_driver.py) & [packet_parser.py](file:///e:/github/transp-agk-sensorsgas/packet_parser.py)

---

## 1. General Communication Settings

The sensor module uses serial communication with the following parameters:

| Parameter | Value |
| :--- | :--- |
| **Baud Rate** | 9600 |
| **Data Bits** | 8 bits |
| **Stop Bit** | 1 bit |
| **Parity** | None |
| **Voltage Level** | 3.3V UART (5V compatible) |

**Communication Modes:**
* **Active Upload:** The sensor automatically sends data periodically.
* **Q & A (Passive):** The sensor waits for a request command before transmitting data.
* **Default:** The module defaults to **Q & A mode** after power-on.

---

## 2. Checksum Algorithm

For most byte frames, the checksum is calculated using the following logic:
1. **Sum** the specified data bytes (typically starting from Byte 1 up to the byte immediately preceding the checksum).
2. **Invert** the bits of the result (bitwise NOT `~`).
3. **Add 1** to the result.

$$\text{Checksum} = (\sim \text{Sum of Bytes}) + 1$$

---

## 3. Mode Switching Commands

### 3.1 Switch to Active Upload Mode
Sets the module to automatically transmit data frames.

| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Byte 5 | Byte 6 | Byte 7 | Byte 8 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | **Retain** | **Cmd** | **Mode** | **Retain** | **Retain** | **Retain** | **Retain** | **Check** |
| `0xFF` | `0x01` | `0x78` | `0x40` | `0x00` | `0x00` | `0x00` | `0x00` | `0x47` |

### 3.2 Switch to Q & A (Passive) Mode
Sets the module to wait for explicit host requests.

| Byte 0 | Byte 1 | Byte 2 | Byte 3 | Byte 4 | Byte 5 | Byte 6 | Byte 7 | Byte 8 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Start** | **Retain** | **Cmd** | **Mode** | **Retain** | **Retain** | **Retain** | **Retain** | **Check** |
| `0xFF` | `0x01` | `0x78` | `0x41` | `0x00` | `0x00` | `0x00` | `0x00` | `0x46` |

---

## 4. Data Reading Commands

### 4.1 Read Gas Concentration Only
**Command (Hex):** `FF 01 86 00 00 00 00 00 79`

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
* **Gas Concentration Value:** `(High Byte * 256) + Low Byte`

### 4.2 Read Combined Data (Gas, Temp, Humidity)
**Command (Hex):** `FF 00 B7 00 00 00 00 00 79` or `FF 01 87 00 00 00 00 00 78`

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
* **Temperature (°C):** `((Temp_High << 8) | Temp_Low) / 100`
* **Humidity (%RH):** `((Hum_High << 8) | Hum_Low) / 100`

---

## 5. Module Information Commands

### 5.1 Get Sensor Info (Basic)
**Command (Hex):** `D1`

**Response:**
| Byte | Description | Notes |
| :--- | :--- | :--- |
| 0 | Sensor Type | e.g., `0x19` for CO |
| 1 | Max Range High | |
| 2 | Max Range Low | |
| 3 | Unit | `0x02` = ppm/mg/m³, `0x04` = ppb/ug/m³ |
| 7 | Decimal & Sign | See decoding below |
| 8 | Parity Bit | |

**Decoding Byte 7 (Decimal & Sign):**
* **Decimal Places:** Bits `[4]-[7]` (Max 3).
* **Sign:** Bits `[0]-[3]`. `0` = Positive, `1` = Negative.

### 5.2 Sensor Type Codes
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
**Enter Sleep:** `AF 53 6C 65 65 70` (Response: `4F 4B` / OK)  
**Exit Sleep:** `AE 45 78 69 74` (Response: `4F 4B` / OK - Wait 5 seconds before sampling)

### 6.2 LED Control (Running Lights)
* **Turn Off LED:** `FF 01 88 00 00 00 00 00 77`
* **Turn On LED:** `FF 01 89 00 00 00 00 00 76`
* **Query LED Status:** `FF 01 8A 00 00 00 00 00 75` (Response Byte 2: `0x01` = On, `0x00` = Off)