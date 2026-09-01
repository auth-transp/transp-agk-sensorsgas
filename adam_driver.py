import serial
import time
import re
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

class AdamModule:
    """
    Driver for Advantech ADAM-4000 series analog input modules (ADAM-4017+, ADAM-4019+, etc.)
    using Advantech ASCII protocol.
    """
    def __init__(self, port, baudrate=9600, address="01", model="ADAM-4017+", timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.model = model
        self.timeout = timeout

    def read_module_name(self, ser=None):
        """
        Sends '$AAM\\r' command to read module name (e.g., '4017+', '4019+').
        """
        cmd = f"${self.address}M\r".encode('ascii')
        own_serial = False
        if ser is None:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            own_serial = True

        try:
            ser.write(cmd)
            resp = ser.read_until(b'\r').decode('ascii').strip()
            if resp.startswith('!'):
                return resp[3:]  # Strip '!AA' header
            return None
        except Exception as e:
            print(f"ADAM Module Name Query Error: {e}")
            return None
        finally:
            if own_serial:
                ser.close()

    def read_firmware_version(self, ser=None):
        """
        Sends '$AAF\\r' command to query firmware version.
        """
        cmd = f"${self.address}F\r".encode('ascii')
        own_serial = False
        if ser is None:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            own_serial = True

        try:
            ser.write(cmd)
            resp = ser.read_until(b'\r').decode('ascii').strip()
            if resp.startswith('!'):
                return resp[3:]
            return None
        except Exception as e:
            print(f"ADAM Firmware Query Error: {e}")
            return None
        finally:
            if own_serial:
                ser.close()

    def read_all_channels(self, ser=None):
        """
        Sends '#AA\\r' command to read all 8 analog channels via Advantech ASCII protocol.
        Compatible with both ADAM-4017+ and ADAM-4019+.
        Returns a list of 8 float values (e.g., in mA or V).
        """
        cmd = f"#{self.address}\r".encode('ascii')
        own_serial = False
        if ser is None:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            own_serial = True

        try:
            ser.write(cmd)
            resp = ser.read_until(b'\r').decode('ascii').strip()

            # Expected response: >+04.000+04.000...
            if resp.startswith('>'):
                data = resp[1:]
                # Extract all numbers formatted like +04.000, -01.234, or +888888
                matches = re.findall(r'[-+]\d+(?:\.\d+)?', data)
                if len(matches) == 8:
                    return [float(m) for m in matches]
            return None
        except Exception as e:
            print(f"ADAM Read Error: {e}")
            return None
        finally:
            if own_serial:
                ser.close()

# Aliases for explicit module class names
Adam4017 = AdamModule
Adam4019 = AdamModule


class AdamThread(QThread):
    data_received = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, port, baudrate=9600, address="01", model="ADAM-4017+"):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.model = model
        self.is_running = False

    def run(self):
        self.is_running = True
        adam = AdamModule(self.port, self.baudrate, self.address, model=self.model)
        try:
            with serial.Serial(self.port, self.baudrate, timeout=1.0) as ser:
                while self.is_running:
                    vals = adam.read_all_channels(ser)
                    if vals:
                        self.data_received.emit(vals)
                    else:
                        self.error_occurred.emit(f"Invalid or missing response from {self.model} module.")
                    time.sleep(1.0)
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.is_running = False

    def stop(self):
        self.is_running = False
        self.wait()


class AdamManager:
    """Manages shared ADAM-4017+/ADAM-4019+ modules across multiple sensors to prevent COM port collisions."""
    def __init__(self):
        self.threads = {} # port -> AdamThread
        self.subscribers = {} # port -> set of callbacks
        self.mutex = QMutex()

    def subscribe(self, port, callback, model="ADAM-4017+"):
        with QMutexLocker(self.mutex):
            if port not in self.subscribers:
                self.subscribers[port] = set()
            self.subscribers[port].add(callback)

            if port not in self.threads:
                print(f"Starting new ADAM thread for port {port} ({model})")
                thread = AdamThread(port, model=model)
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
                    print(f"Stopping ADAM thread for port {port}")
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
adam_manager = AdamManager()
