
from sensor_driver import TB200BSensor
from packet_parser import parse_combined_response, validate_checksum
import time

def verify():
    print("Testing patched sensor driver...")
    sensor = TB200BSensor(port="COM7", baudrate=9600)
    try:
        sensor.connect()
        sensor.set_passive_mode()
        time.sleep(1)
        
        print("Requesting combined data (now using 0x87)...")
        raw_data = sensor.read_combined_data()
        
        if raw_data:
            print(f"Received {len(raw_data)} bytes: {raw_data.hex()}")
            if validate_checksum(raw_data):
                print("Checksum Valid!")
                try:
                    parsed = parse_combined_response(raw_data)
                    print(f"Parsed Data: {parsed}")
                    print("VERIFICATION SUCCESS: Data received and parsed correctly.")
                except Exception as e:
                    print(f"VERIFICATION FAILED: Parsing error: {e}")
            else:
                print("VERIFICATION FAILED: Checksum invalid.")
        else:
            print("VERIFICATION FAILED: No data received.")
            
    except Exception as e:
        print(f"VERIFICATION FAILED: Exception: {e}")
    finally:
        sensor.disconnect()

if __name__ == "__main__":
    verify()
