"""
ADAM-4017+ / ADAM-4019+ Terminal Debug Tool
===========================================
Interactive terminal tool for testing and debugging ADAM-4017+ and ADAM-4019+ connections.

Usage:
    python adam_debug.py

Commands:
    scan        - Scan all available COM ports
    open <port> - Open a serial connection (e.g. open COM3)
    close       - Close the current connection
    read        - Read all 8 analog channels
    loop [n]    - Continuously read channels (n seconds interval, default 1)
    raw <cmd>   - Send a raw ASCII command and print the response
    config      - Query module name ($AAM) and firmware version ($AAF)
    addr <AA>   - Change the target ADAM address (default: 01)
    baud <rate> - Change baud rate (default: 9600)
    cal <ch> <base_ma> <max_ma> <max_gas> - Apply calibration to a channel
    help        - Show this help
    quit        - Exit
"""

import serial
import serial.tools.list_ports
import time
import sys
import re

# Defaults
current_port = None
current_ser = None
adam_address = "01"
baud_rate = 9600
calibrations = {}  # ch -> (base_ma, max_ma, max_gas, label)


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
    global current_ser, current_port
    if current_ser and current_ser.is_open:
        print(f"  Closing existing connection on {current_port}...")
        current_ser.close()
    try:
        current_ser = serial.Serial(port_name, baud_rate, timeout=1.0)
        current_port = port_name
        print(f"  Opened {port_name} at {baud_rate} baud.")
    except Exception as e:
        print(f"  ERROR: Could not open {port_name}: {e}")
        current_ser = None
        current_port = None


def close_port():
    global current_ser, current_port
    if current_ser and current_ser.is_open:
        current_ser.close()
        print(f"  Closed {current_port}.")
    else:
        print("  No port is open.")
    current_ser = None
    current_port = None


def send_raw(cmd_str):
    if not current_ser or not current_ser.is_open:
        print("  ERROR: No port open. Use 'open <port>' first.")
        return None
    try:
        cmd_bytes = (cmd_str + "\r").encode('ascii')
        print(f"  TX: {repr(cmd_bytes)}")
        current_ser.reset_input_buffer()
        current_ser.write(cmd_bytes)
        resp = current_ser.read_until(b'\r')
        resp_str = resp.decode('ascii', errors='replace').rstrip('\r\n')
        print(f"  RX: {repr(resp_str)}  ({len(resp)} bytes)")
        return resp_str
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def parse_channels(resp_str):
    if not resp_str or not resp_str.startswith('>'):
        return None
    data = resp_str[1:]  # strip leading '>'

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
    matches = re.findall(r'[-+]\d+(?:\.\d+)?', data)
    if len(matches) == 8:
        return [float(m) for m in matches]

    return None


def read_channels():
    resp = send_raw(f"#{adam_address}")
    if resp is None:
        return
    vals = parse_channels(resp)
    if vals is None:
        print("  Could not parse channel data.")
        return
    print()
    print(f"  {'Ch':<5} {'Raw (mA/mV)':<12} {'Calibrated':<15} {'Label'}")
    print(f"  {'--':<5} {'-----------':<12} {'----------':<15} {'-----'}")
    for ch, raw in enumerate(vals):
        if ch in calibrations:
            base_ma, max_ma, max_gas, label = calibrations[ch]
            span = max_ma - base_ma
            cal_val = (raw - base_ma) * (max_gas / span) if span != 0 else 0.0
            print(f"  {ch:<5} {raw:<12.4f} {cal_val:<15.2f} {label}")
        else:
            print(f"  {ch:<5} {raw:<12.4f} {'--':<15} {'(no cal)'}")


def read_loop(interval):
    print(f"  Continuous read every {interval}s. Press Ctrl+C to stop.\n")
    # Print header
    header = f"  {'Time':<12}"
    for ch in range(8):
        if ch in calibrations:
            _, _, _, label = calibrations[ch]
            header += f" {f'Ch{ch}({label})':<14}"
        else:
            header += f" {f'Ch{ch}':<14}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    try:
        while True:
            resp = send_raw(f"#{adam_address}")
            if resp is None:
                time.sleep(interval)
                continue
            vals = parse_channels(resp)
            if vals is None:
                print("  Parse error.")
                time.sleep(interval)
                continue

            ts = time.strftime("%H:%M:%S")
            line = f"  {ts:<12}"
            for ch, raw in enumerate(vals):
                if ch in calibrations:
                    base_ma, max_ma, max_gas, _ = calibrations[ch]
                    span = max_ma - base_ma
                    cal_val = (raw - base_ma) * (max_gas / span) if span != 0 else 0.0
                    line += f" {cal_val:<14.2f}"
                else:
                    line += f" {raw:<14.4f}"
            print(line)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Stopped.")


def set_calibration(args):
    try:
        parts = args.split()
        ch = int(parts[0])
        base_ma = float(parts[1])
        max_ma = float(parts[2])
        max_gas = float(parts[3])
        label = parts[4] if len(parts) > 4 else f"Ch{ch}"
        calibrations[ch] = (base_ma, max_ma, max_gas, label)
        print(f"  Ch{ch}: {base_ma} -> 0, {max_ma} -> {max_gas} [{label}]")
    except (IndexError, ValueError):
        print("  Usage: cal <ch> <base_val> <max_val> <max_gas> [label]")
        print("  Example: cal 0 4.0 20.0 25.0 O2%")


def query_config():
    name_resp = send_raw(f"${adam_address}M")
    fw_resp = send_raw(f"${adam_address}F")
    if name_resp and name_resp.startswith('!'):
        print(f"  Detected Module Model: ADAM-{name_resp[3:]}")
    if fw_resp and fw_resp.startswith('!'):
        print(f"  Firmware Version: {fw_resp[3:]}")


def show_help():
    print(__doc__)


def main():
    global adam_address, baud_rate

    print("=" * 60)
    print("  ADAM-4017+ / ADAM-4019+ Debug Terminal")
    print("=" * 60)
    print("  Type 'help' for commands.\n")

    while True:
        try:
            status = f"[{current_port or 'no port'}@{baud_rate}|addr:{adam_address}]"
            cmd = input(f"  ADAM {status} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action == "quit" or action == "exit":
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
        elif action == "raw":
            if not arg:
                print("  Usage: raw <command>  (e.g. raw #01)")
            else:
                send_raw(arg)
        elif action == "config":
            query_config()
        elif action == "addr":
            if arg:
                adam_address = arg.strip().zfill(2)
                print(f"  Address set to: {adam_address}")
            else:
                print(f"  Current address: {adam_address}")
        elif action == "baud":
            if arg:
                baud_rate = int(arg)
                print(f"  Baud rate set to: {baud_rate}")
                if current_ser and current_ser.is_open:
                    print("  Note: Close and re-open the port for the new baud rate to take effect.")
            else:
                print(f"  Current baud rate: {baud_rate}")
        elif action == "cal":
            set_calibration(arg)
        else:
            print(f"  Unknown command: '{action}'. Type 'help' for commands.")

    if current_ser and current_ser.is_open:
        current_ser.close()
        print(f"  Closed {current_port}.")
    print("  Goodbye.")


if __name__ == "__main__":
    main()
