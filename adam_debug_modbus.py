"""
ADAM-4017+ Modbus Debug Tool
==============================
Interactive terminal tool for testing and debugging ADAM-4017+ connections via Modbus RTU.

Usage:
    python adam_debug_modbus.py

Commands:
    scan        - Scan all available COM ports
    open <port> - Open a Modbus connection (e.g. open COM3)
    close       - Close the current connection
    read        - Read all 8 analog channels via Modbus holding registers
    loop [n]    - Continuously read channels (n seconds interval, default 1)
    addr <AA>   - Change the target ADAM Modbus slave address (default: 1)
    baud <rate> - Change baud rate (default: 9600)
    cal <ch> <base_raw> <max_raw> <max_gas> - Apply calibration to a channel
    help        - Show this help
    quit        - Exit
"""

import serial.tools.list_ports
import time
import sys
from pymodbus.client import ModbusSerialClient

# Defaults
current_port = None
current_client = None
adam_address = 1
baud_rate = 9600
calibrations = {}  # ch -> (base_raw, max_raw, max_gas, label)


def scan_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("  No COM ports found.")
        return
    print(f"  {'Port':<10} {'VID:PID':<12} {'Serial Number':<20} {'Description'}")
    print(f"  {'----':<10} {'-------':<12} {'-------------':<20} {'-----------'}")
    for p in ports:
        vid_pid = f"{p.vid:04X}:{p.pid:04X}" if p.vid else "N/A"
        sn = p.serial_number or "N/A"
        print(f"  {p.device:<10} {vid_pid:<12} {sn:<20} {p.description}")


def open_port(port_name):
    global current_client, current_port
    if current_client and current_client.connected:
        print(f"  Closing existing connection on {current_port}...")
        current_client.close()
    try:
        current_client = ModbusSerialClient(port=port_name, baudrate=baud_rate, timeout=1.0)
        success = current_client.connect()
        if success:
            current_port = port_name
            print(f"  Opened {port_name} at {baud_rate} baud.")
        else:
            print(f"  ERROR: Could not connect to {port_name}")
            current_client = None
            current_port = None
    except Exception as e:
        print(f"  ERROR: {e}")
        current_client = None
        current_port = None


def close_port():
    global current_client, current_port
    if current_client and current_client.connected:
        current_client.close()
        print(f"  Closed {current_port}.")
    else:
        print("  No port is open.")
    current_client = None
    current_port = None


def read_channels():
    if not current_client or not current_client.connected:
        print("  ERROR: No port open. Use 'open <port>' first.")
        return None
        
    try:
        # Holding registers 40001-40008 (address 0 to 7)
        result = current_client.read_holding_registers(address=0, count=8, slave=adam_address)
        if result.isError():
            print(f"  Modbus Error: {result}")
            return None
            
        vals = result.registers
        print()
        print(f"  {'Ch':<5} {'Raw (int)':<12} {'Calibrated':<15} {'Label'}")
        print(f"  {'--':<5} {'---------':<12} {'----------':<15} {'-----'}")
        for ch, raw in enumerate(vals):
            if ch in calibrations:
                base_raw, max_raw, max_gas, label = calibrations[ch]
                span = max_raw - base_raw
                cal_val = (raw - base_raw) * (max_gas / span) if span != 0 else 0.0
                print(f"  {ch:<5} {raw:<12d} {cal_val:<15.2f} {label}")
            else:
                print(f"  {ch:<5} {raw:<12d} {'--':<15} {'(no cal)'}")
        return vals
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def read_loop(interval):
    print(f"  Continuous read every {interval}s. Press Ctrl+C to stop.\n")
    # Print header
    header = f"  {'Time':<12}"
    for ch in range(8):
        if ch in calibrations:
            _, _, _, label = calibrations[ch]
            header += f" {f'Ch{ch}({label})':<14}"
        else:
            header += f" {f'Ch{ch}(int)':<14}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    
    try:
        while True:
            if not current_client or not current_client.connected:
                 print("  Connection lost.")
                 break
                 
            result = current_client.read_holding_registers(address=0, count=8, slave=adam_address)
            if result.isError():
                time.sleep(interval)
                continue
                
            vals = result.registers
            ts = time.strftime("%H:%M:%S")
            line = f"  {ts:<12}"
            for ch, raw in enumerate(vals):
                if ch in calibrations:
                    base_raw, max_raw, max_gas, _ = calibrations[ch]
                    span = max_raw - base_raw
                    cal_val = (raw - base_raw) * (max_gas / span) if span != 0 else 0.0
                    line += f" {cal_val:<14.2f}"
                else:
                    line += f" {raw:<14d}"
            print(line)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Stopped.")


def set_calibration(args):
    try:
        parts = args.split()
        ch = int(parts[0])
        base_raw = float(parts[1])
        max_raw = float(parts[2])
        max_gas = float(parts[3])
        label = parts[4] if len(parts) > 4 else f"Ch{ch}"
        calibrations[ch] = (base_raw, max_raw, max_gas, label)
        print(f"  Ch{ch}: {base_raw} int -> 0, {max_raw} int -> {max_gas} [{label}]")
    except (IndexError, ValueError):
        print("  Usage: cal <ch> <base_raw> <max_raw> <max_gas> [label]")
        print("  Example: cal 0 13107 65535 25.0 O2%")


def show_help():
    print(__doc__)


def main():
    global adam_address, baud_rate
    
    print("=" * 60)
    print("  ADAM-4017+ Modbus Debug Terminal")
    print("=" * 60)
    print("  Type 'help' for commands.\n")
    
    while True:
        try:
            status = f"[{current_port or 'no port'}@{baud_rate}|slave:{adam_address}]"
            cmd = input(f"  ADAM {status} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break
        
        if not cmd:
            continue
        
        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if action in ("quit", "exit"):
            break
        elif action == "help":
            show_help()
        elif action == "scan":
            scan_ports()
        elif action == "open":
            if not arg:
                print("  Usage: open <port>  (e.g. open COM3)")
            else:
                open_port(arg.strip())
        elif action == "close":
            close_port()
        elif action == "read":
            read_channels()
        elif action == "loop":
            interval = float(arg) if arg else 1.0
            read_loop(interval)
        elif action == "addr":
            if arg:
                try:
                    adam_address = int(arg.strip())
                    print(f"  Slave address set to: {adam_address}")
                except ValueError:
                    print("  Address must be an integer.")
            else:
                print(f"  Current slave address: {adam_address}")
        elif action == "baud":
            if arg:
                try:
                    baud_rate = int(arg)
                    print(f"  Baud rate set to: {baud_rate}")
                    if current_client and current_client.connected:
                        print("  Note: Close and re-open the port for the new baud rate to take effect.")
                except ValueError:
                    print("  Baud rate must be an integer.")
            else:
                print(f"  Current baud rate: {baud_rate}")
        elif action == "cal":
            set_calibration(arg)
        else:
            print(f"  Unknown command: '{action}'. Type 'help' for commands.")
    
    if current_client and current_client.connected:
        current_client.close()
        print(f"  Closed {current_port}.")
    print("  Goodbye.")


if __name__ == "__main__":
    main()
