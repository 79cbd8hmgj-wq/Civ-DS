"""Strict Nintendo LZ10 decompression."""
from civds.errors import FormatError

def is_lz10(data: bytes) -> bool:
    return len(data) >= 4 and data[0] == 0x10 and int.from_bytes(data[1:4], "little") > 0

def decompress(data: bytes) -> bytes:
    if not is_lz10(data):
        raise FormatError("not an LZ10 stream")
    expected = int.from_bytes(data[1:4], "little")
    source = 4
    output = bytearray()
    while len(output) < expected:
        if source >= len(data):
            raise FormatError("truncated LZ10 flags")
        flags = data[source]
        source += 1
        for bit in range(7, -1, -1):
            if len(output) == expected:
                break
            if flags & (1 << bit):
                if source + 2 > len(data):
                    raise FormatError("truncated LZ10 back-reference")
                pair = (data[source] << 8) | data[source + 1]
                source += 2
                length = (pair >> 12) + 3
                distance = (pair & 0xFFF) + 1
                if distance > len(output) or len(output) + length > expected:
                    raise FormatError("invalid LZ10 back-reference")
                for _ in range(length):
                    output.append(output[-distance])
            else:
                if source >= len(data):
                    raise FormatError("truncated LZ10 literal")
                output.append(data[source])
                source += 1
    return bytes(output)
