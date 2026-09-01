from pymodbus.client import ModbusSerialClient
import time
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

class AdamModuleModbus:
    """
    Driver for Advantech ADAM-4000 series analog input modules (ADAM-4017+, ADAM-4019+, etc.)
    using Modbus RTU protocol.
    """
    def __init__(self, port, baudrate=9600, address=1, model="ADAM-4017+", timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.address = int(address)
        self.model = model
        self.timeout = timeout

    def read_all_channels(self, client=None):
        """
        Reads 8 analog channels via Modbus RTU using holding registers 40001-40008 (address 0-7).
        Compatible with both ADAM-4017+ and ADAM-4019+.
        Returns a list of 8 integer values.
        """
        own_client = False
        if client is None:
            client = ModbusSerialClient(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            client.connect()
            own_client = True

        try:
            # Holding registers 40001-40008 (address 0-7)
            result = client.read_holding_registers(address=0, count=8, slave=self.address)
            if not result.isError():
                return result.registers
            else:
                print(f"ADAM Modbus Error ({self.model}): {result}")
                return None
        except Exception as e:
            print(f"ADAM Modbus Exception ({self.model}): {e}")
            return None
        finally:
            if own_client:
                client.close()

# Aliases for explicit module class names
Adam4017Modbus = AdamModuleModbus
Adam4019Modbus = AdamModuleModbus


class AdamThreadModbus(QThread):
    data_received = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate=9600, address=1, model="ADAM-4017+"):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.address = int(address)
        self.model = model
        self.is_running = False

    def run(self):
        self.is_running = True
        adam = AdamModuleModbus(self.port, self.baudrate, self.address, model=self.model)
        try:
            with ModbusSerialClient(port=self.port, baudrate=self.baudrate, timeout=1.0) as client:
                client.connect()
                while self.is_running:
                    vals = adam.read_all_channels(client)
                    if vals is not None:
                        self.data_received.emit(vals)
                    else:
                        self.error_occurred.emit(f"Invalid or missing response from {self.model} Modbus module.")
                    time.sleep(1.0)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.is_running = False

    def stop(self):
        self.is_running = False
        self.wait()


class AdamManagerModbus:
    """Manages shared ADAM-4017+/ADAM-4019+ modules via Modbus to prevent COM port collisions."""
    def __init__(self):
        self.threads = {} # port -> AdamThreadModbus
        self.subscribers = {} # port -> set of callbacks
        self.mutex = QMutex()

    def subscribe(self, port, callback, model="ADAM-4017+"):
        with QMutexLocker(self.mutex):
            if port not in self.subscribers:
                self.subscribers[port] = set()
            self.subscribers[port].add(callback)

            if port not in self.threads:
                print(f"Starting new ADAM Modbus thread for port {port} ({model})")
                thread = AdamThreadModbus(port, model=model)
                thread.data_received.connect(lambda vals, p=port: self._broadcast(p, vals))
                self.threads[port] = thread
                thread.start()

    def unsubscribe(self, port, callback):
        with QMutexLocker(self.mutex):
            if port in self.subscribers and callback in self.subscribers[port]:
                self.subscribers[port].remove(callback)

            if not self.subscribers.get(port):
                # No more sensors need this ADAM module, safe to close port
                if port in self.threads:
                    print(f"Stopping ADAM Modbus thread for port {port}")
                    self.threads[port].stop()
                    del self.threads[port]
                if port in self.subscribers:
                    del self.subscribers[port]

    def _broadcast(self, port, vals):
        with QMutexLocker(self.mutex):
            if port in self.subscribers:
                for callback in self.subscribers[port]:
                    callback(vals)

# Global singleton
adam_manager_modbus = AdamManagerModbus()
