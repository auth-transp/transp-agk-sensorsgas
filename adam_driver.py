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

        The ADAM-4019+ (and some 4017+ firmware versions) uses a fixed-width
        7-character-per-channel format where inactive/unconfigured channels are
        returned as 7 spaces rather than a signed numeric value. The old regex
        approach only matched explicitly-signed values and therefore missed
        space-padded channels, returning fewer than 8 matches.

        This implementation parses the 56-byte data body (after the leading '>')
        as eight consecutive 7-character fields and converts space-only fields to
        0.0 so that all 8 channel values are always returned.
        """
        cmd = f"#{self.address}\r".encode('ascii')
        own_serial = False
        if ser is None:
            ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            own_serial = True

        try:
            ser.write(cmd)
            resp = ser.read_until(b'\r').decode('ascii').rstrip('\r\n')

            if not resp.startswith('>'):
                return None

            data = resp[1:]  # Strip leading '>'

            # --- Primary: fixed-width 7-char per channel (ADAM-4019+ format) ---
            # Response body is exactly 56 chars (8 channels × 7 chars each).
            # Inactive channels appear as 7 spaces; active ones as e.g. '+009.73'.
            if len(data) >= 56:
                values = []
                for i in range(8):
                    chunk = data[i * 7:(i + 1) * 7]
                    stripped = chunk.strip()
                    try:
                        values.append(float(stripped) if stripped else 0.0)
                    except ValueError:
                        values.append(0.0)
                return values

            # --- Fallback: regex for older ADAM-4017+ compact format ---
            # Some firmware versions omit the space-padding and return only
            # signed numeric tokens separated directly (e.g. '+04.000+04.000...')
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

        while self.is_running:
            try:
                with serial.Serial(self.port, self.baudrate, timeout=1.0) as ser:
                    self.error_occurred.emit(f"{self.model} connected on {self.port}")
                    consecutive_failures = 0
                    while self.is_running:
                        vals = adam.read_all_channels(ser)
                        if vals is not None:
                            consecutive_failures = 0
                            self.data_received.emit(vals)
                        else:
                            consecutive_failures += 1
                            self.error_occurred.emit(
                                f"{self.model}: no valid response (attempt {consecutive_failures})"
                            )
                            if consecutive_failures >= 5:
                                # Break inner loop to trigger reconnect
                                break
                        time.sleep(1.0)
            except Exception as e:
                self.error_occurred.emit(f"{self.model} on {self.port}: {e}")

            if self.is_running:
                # Wait 3 s before reconnect attempt
                for _ in range(30):
                    if not self.is_running:
                        break
                    time.sleep(0.1)

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
