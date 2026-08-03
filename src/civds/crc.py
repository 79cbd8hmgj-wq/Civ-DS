"""Nintendo DS CRC-16 calculation."""


def crc16(data: bytes, initial: int = 0xFFFF) -> int:
    value = initial
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value & 0xFFFF
