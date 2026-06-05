
def calculate_checksum(data: list[int]) -> int:
    """
    Calculates checksum for TB200B/TB600B commands.
    Algorithm: Sum bytes (excluding start/end), invert, then add 1.
    """
    # Sum bytes (typically from index 1 up to N-1)
    checksum = sum(data)
    checksum = (~checksum) & 0xFF
    checksum += 1
    return checksum & 0xFF

def validate_checksum(packet: bytes) -> bool:
    """
    Validates the checksum of a received packet.
    The last byte is the received checksum.
    The sum is calculated on packet[1:-1].
    """
    if len(packet) < 3:
        return False
    
    # According to doc: Sum Bytes 1-(N-1)
    calculated = calculate_checksum(list(packet[1:-1]))
    received = packet[-1]
    
    return calculated == received

def parse_gas_concentration_response(packet: bytes) -> dict:
    """
    Parses response for Command 5 (0x86).
    Returns dictionary with parsed values.
    """
    if len(packet) != 9:
        raise ValueError("Invalid packet length for Gas Response (expected 9)")
    
    # Byte 2: High Gas (ug/m3), Byte 3: Low Gas
    gas_ug_m3 = (packet[2] << 8) | packet[3]
    
    # Byte 6: High Gas (ppb), Byte 7: Low Gas
    gas_ppb = (packet[6] << 8) | packet[7]
    
    return {
        "gas_ug_m3": gas_ug_m3,
        "gas_ppb": gas_ppb
    }

def parse_combined_response(packet: bytes) -> dict:
    """
    Parses response for Command 6 (0xB7).
    Returns dictionary with gas, temp, humidity.
    """
    if len(packet) != 13: # 0xFF 0x87 ... plus check
        raise ValueError(f"Invalid packet length for Combined Response (expected 13, got {len(packet)})")
    
    # Gas
    gas_ug_m3 = (packet[2] << 8) | packet[3]
    gas_ppb = (packet[6] << 8) | packet[7]
    
    # Temperature (Signed)
    temp_raw = (packet[8] << 8) | packet[9]
    if temp_raw > 32767:
        temp_raw -= 65536
    temperature = temp_raw / 100.0
    
    # Humidity (Unsigned)
    hum_raw = (packet[10] << 8) | packet[11]
    humidity = hum_raw / 100.0
    
    return {
        "gas_ug_m3": gas_ug_m3,
        "gas_ppb": gas_ppb,
        "temperature_c": temperature,
        "humidity_rh": humidity
    }
