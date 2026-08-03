"""Nintendo DS backward-LZ (BLZ) decoder used by compressed overlays."""

from __future__ import annotations
from dataclasses import dataclass
from civds.errors import FormatError


@dataclass(frozen=True)
class Footer:
    compressed_size: int
    header_size: int
    added_size: int


def footer(data: bytes) -> Footer | None:
    if len(data) < 8:
        return None
    descriptor = int.from_bytes(data[-8:-4], "little")
    result = Footer(descriptor & 0xFFFFFF, descriptor >> 24, int.from_bytes(data[-4:], "little"))
    if result.added_size == 0:
        return None
    if (
        result.header_size < 8
        or result.header_size > 0xB
        or result.compressed_size < result.header_size
        or result.compressed_size > len(data)
    ):
        return None
    return result


def decompress(data: bytes) -> bytes:
    metadata = footer(data)
    if metadata is None:
        raise FormatError("not a valid BLZ stream")
    source_floor = len(data) - metadata.compressed_size
    source = len(data) - metadata.header_size
    destination = len(data) + metadata.added_size
    output = bytearray(data)
    output.extend(b"\0" * metadata.added_size)
    while destination > source_floor:
        if source <= source_floor:
            raise FormatError("truncated BLZ flags")
        source -= 1
        flags = output[source]
        for _ in range(8):
            if destination <= source_floor:
                break
            if flags & 0x80:
                if source - 2 < source_floor:
                    raise FormatError("truncated BLZ back-reference")
                source -= 2
                token = output[source] | (output[source + 1] << 8)
                count = (token >> 12) + 3
                distance = (token & 0xFFF) + 3
                if count > destination - source_floor:
                    raise FormatError("BLZ back-reference overruns output")
                for _ in range(count):
                    destination -= 1
                    lookup = destination + distance
                    if lookup >= len(output):
                        raise FormatError("invalid BLZ back-reference distance")
                    output[destination] = output[lookup]
            else:
                if source <= source_floor:
                    raise FormatError("truncated BLZ literal")
                source -= 1
                destination -= 1
                output[destination] = output[source]
            flags = (flags << 1) & 0xFF
    if destination != source_floor:
        raise FormatError("BLZ output size mismatch")
    return bytes(output)
