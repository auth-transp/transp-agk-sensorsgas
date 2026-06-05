
import serial
import time
from typing import Optional

class TB200BSensor:
    def __init__(self, port: str = "COM3", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None

    def connect(self):
        """Opens the serial connection."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2 # 2 second timeout
            )
            print(f"Connected to {self.port}")
        except serial.SerialException as e:
            print(f"Error connecting to serial port: {e}")
            raise

    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            print("Disconnected")

    def _send_command(self, cmd: list[int]):
        """Sends a byte command list to the sensor."""
        if not self.ser:
            raise Exception("Not connected")
        self.ser.reset_input_buffer()
        self.ser.write(bytes(cmd))
        
    def set_active_mode(self):
        """Switch to Active Upload Mode."""
        # 0xFF 0x01 0x78 0x40 0x00 0x00 0x00 0x00 0x47
        cmd = [0xFF, 0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00, 0x47]
        self._send_command(cmd)
        if self.ser:
            self.ser.read(9) # Clear ACK
        print("Set to Active Mode")

    def set_passive_mode(self):
        """Switch to Passive (Q&A) Mode."""
        # 0xFF 0x01 0x78 0x41 0x00 0x00 0x00 0x00 0x46
        cmd = [0xFF, 0x01, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00, 0x46]
        self._send_command(cmd)
        if self.ser:
            self.ser.read(9) # Clear ACK
        print("Set to Passive Mode")
        
    def set_led(self, state: bool):
        """Turn the sensor LED on or off."""
        if state:
            # Turn On: FF 01 89 00 00 00 00 00 76
            cmd = [0xFF, 0x01, 0x89, 0x00, 0x00, 0x00, 0x00, 0x00, 0x76]
        else:
            # Turn Off: FF 01 88 00 00 00 00 00 77
            cmd = [0xFF, 0x01, 0x88, 0x00, 0x00, 0x00, 0x00, 0x00, 0x77]
        self._send_command(cmd)
        if self.ser:
            self.ser.read(9) # Clear ACK
        
    def read_gas_concentration(self) -> Optional[bytes]:
        """Request (0x86) and read gas concentration."""
        # Request: 0xFF 0x01 0x86 0x00 0x00 0x00 0x00 0x00 0x79
        cmd = [0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]
        self._send_command(cmd)
        # Response is 9 bytes
        return self.ser.read(9)

    def read_combined_data(self) -> Optional[bytes]:
        """Request (0x87) and read combined gas/temp/hum data."""
        # Request: 0xFF 0x01 0x87 0x00 0x00 0x00 0x00 0x00 0x78
        # This is the command variant that effectively works for this sensor version.
        
        cmd = [0xFF, 0x01, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00]
        
        # Calculate checksum dynamically
        chk = (sum(cmd[1:]) ^ 0xFF) + 1
        chk = chk & 0xFF
        cmd.append(chk)
        
        self._send_command(cmd)
        # Response is 13 bytes
        return self.ser.read(13)
        
    def read_packet(self, size=9) -> bytes:
        """Reads a specific number of bytes from the buffer."""
        if self.ser and self.ser.in_waiting >= size:
            return self.ser.read(size)
        return b''
