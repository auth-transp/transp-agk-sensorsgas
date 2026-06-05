import time
import threading
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal
from sensor_driver import TB200BSensor
from packet_parser import parse_combined_response, validate_checksum

class SensorThread(QThread):
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    sensor_info_received = pyqtSignal(str)

    def __init__(self, serial_number, baudrate=9600, gas_type="CO", brand="ECSense", parent=None):
        super().__init__(parent)
        self.serial_number = serial_number
        self.baudrate = baudrate
        self.gas_type = gas_type
        self.brand = brand
        self.sensor = None
        self.is_running = False
        self._pending_led_state = None

    def set_led_state(self, state: bool):
        self._pending_led_state = state

    def get_port_by_serial(self):
        ports = serial.tools.list_ports.comports()
        
        # 1. Exact SN Match
        for p in ports:
            if self.serial_number and p.serial_number == self.serial_number:
                return p.device
                
        # 2. Fallback: Query FTDI ports for Gas Type
        if self.brand == "ECSense":
            GAS_CODES = {"CO": 0x19, "H2": 0x1B, "O2": 0x22}
            target_code = GAS_CODES.get(self.gas_type)
            if not target_code:
                return None
                
            import serial as pyserial
            for p in ports:
                if p.vid == 0x0403 and p.pid == 0x6001:
                    try:
                        with pyserial.Serial(p.device, self.baudrate, timeout=0.2) as s:
                            s.write(bytes([0xD1]))
                            resp = s.read(9)
                            if len(resp) >= 1 and resp[0] == target_code:
                                # Update our internal SN to the new one so future checks are fast
                                self.serial_number = p.serial_number
                                return p.device
                    except Exception:
                        pass
                        
        elif self.brand == "Membrapor":
            # Membrapor auto-discovery not yet implemented
            pass
                    
        return None

    def run(self):
        self.is_running = True

        while self.is_running:
            self.status_changed.emit("Connecting")
            
            # Dynamically resolve COM port by Serial Number
            port = self.get_port_by_serial()
            if not port:
                self.error_occurred.emit(f"Device with SN {self.serial_number} not found")
                self.status_changed.emit("Error")
            else:
                self.sensor = TB200BSensor(port=port, baudrate=self.baudrate)
                try:
                    self.sensor.connect()
                    self.sensor.set_passive_mode()
                    
                    # Query Sensor Info once
                    try:
                        self.sensor._send_command([0xD1])
                        resp = self.sensor.read_packet(9)
                        if len(resp) == 9:
                            range_val = (resp[1] << 8) | resp[2]
                            unit = "ppb" if resp[3] == 0x04 else "ppm/ug"
                            gas_map = {0x19: "CO", 0x1B: "H2", 0x22: "O2"}
                            gas_name = gas_map.get(resp[0], "Unknown")
                            info_str = f"Max Range: {range_val} {unit} ({gas_name})"
                            self.sensor_info_received.emit(info_str)
                    except Exception:
                        pass
                        
                    self.status_changed.emit("Connected")
                    
                    while self.is_running:
                        if self._pending_led_state is not None:
                            self.sensor.set_led(self._pending_led_state)
                            self._pending_led_state = None
                            
                        try:
                            raw_data = self.sensor.read_combined_data()
                            if raw_data and validate_checksum(raw_data):
                                if len(raw_data) >= 2 and raw_data[1] == 0x87:
                                    parsed = parse_combined_response(raw_data)
                                    self.data_received.emit(parsed)
                        except Exception as e:
                            self.error_occurred.emit(f"Read error: {e}")
                            break # Break inner loop to trigger reconnect
                        
                        time.sleep(1.0)
                        
                except Exception as e:
                    self.error_occurred.emit(f"Connection failed: {e}")
                    self.status_changed.emit("Error")
                
                # Disconnect if breaking inner loop or connection failed
                if self.sensor:
                    self.sensor.disconnect()
            
            # Wait before attempting to reconnect, breaking early if stopped
            for _ in range(50): 
                if not self.is_running:
                    break
                time.sleep(0.1)

        self.status_changed.emit("Disconnected")

    def stop(self):
        self.is_running = False
        self.wait()
