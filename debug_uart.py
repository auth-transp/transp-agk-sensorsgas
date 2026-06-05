
import serial
import time
import argparse

def calculate_checksum(data):
    # Sum bytes 1 to end
    s = sum(data)
    return (~s + 1) & 0xFF

def send_and_read(ser, name, cmd_bytes, expected_len):
    print(f"\n[{name}] Sending: {[hex(b) for b in cmd_bytes]}")
    ser.reset_input_buffer()
    ser.write(bytes(cmd_bytes))
    time.sleep(1.0) # Wait for response
    resp = ser.read(expected_len if expected_len else 100)
    
    if resp:
        print(f"[{name}] Received ({len(resp)} bytes): {[hex(b) for b in resp]}")
        # Verify checksum
        if len(resp) >= 2:
            try:
                # Expected checksum algo
                calc_chk = calculate_checksum(resp[1:-1])
                recv_chk = resp[-1]
                print(f"[{name}] Checksum Valid: {calc_chk == recv_chk} (Calc: {hex(calc_chk)}, Recv: {hex(recv_chk)})")
            except Exception as e:
                print(f"[{name}] Checksum check error: {e}")
    else:
        print(f"[{name}] No response.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--baud", type=int, default=9600)
    args = parser.parse_args()
    
    try:
        ser = serial.Serial(args.port, args.baud, timeout=2.0)
        print(f"Opened {args.port} at {args.baud}")
    except Exception as e:
        print(f"Failed to open port: {e}")
        return

    try:
        # TEST 1: Passive Mode Switch (0x78)
        # 0xFF 0x01 0x78 0x41 ...
        cmd_passive = [0xFF, 0x01, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00, 0x46]
        send_and_read(ser, "Set Passive", cmd_passive, 0) # Response usually none or OK? Doc doesn't say response for mode switch explicit verify?
        # Actually doc doesn't specify response for 3.1/3.2, assume none or echo. 
        # But we need it in passive to test commands.
        
        # TEST 2: Read Gas Only (0x86) - Known good from doc 4.1
        # 0xFF 0x01 0x86 ... 
        cmd_gas = [0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]
        send_and_read(ser, "Read Gas (0x86)", cmd_gas, 9)

        # TEST 3: Read Combined (0xB7) with Calc Checksum (0x49)
        # 0xFF 0x00 0xB7 ...
        # Sum 0x00+0xB7 = 0xB7. ~0xB7+1 = 0x49.
        cmd_b7_calc = [0xFF, 0x00, 0xB7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x49]
        send_and_read(ser, "Read Combined (0xB7, Chk 0x49)", cmd_b7_calc, 13)

        # TEST 4: Read Combined (0xB7) with Doc Checksum (0x79)
        cmd_b7_doc = [0xFF, 0x00, 0xB7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]
        send_and_read(ser, "Read Combined (0xB7, Chk 0x79)", cmd_b7_doc, 13)
        
        # TEST 5: Try 0x87 Command (Standard Pattern) just in case
        # 0xFF 0x01 0x87 ...
        # Sum 0x01+0x87=0x88. ~0x88+1=0x78.
        cmd_87 = [0xFF, 0x01, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78]
        send_and_read(ser, "Read Combined Variant (0x87)", cmd_87, 13)

    finally:
        ser.close()
        print("Closed.")

if __name__ == "__main__":
    main()
