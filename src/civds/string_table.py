"""Parser for the game's STBL localization container."""

from __future__ import annotations
from dataclasses import dataclass
import struct
from .errors import FormatError


@dataclass(frozen=True)
class StringRecord:
    index: int
    key_hash: int
    data_offset: int
    text: str


def parse_stbl(data: bytes, encoding: str = "cp1252") -> list[StringRecord]:
    if len(data) < 24 or data[:4] != b"STBL":
        raise FormatError("not an STBL container")
    version = struct.unpack_from("<I", data, 4)[0]
    count = struct.unpack_from("<I", data, 16)[0]
    if version != 1 or count > (len(data) - 24) // 8:
        raise FormatError("invalid STBL header or record count")
    output: list[StringRecord] = []
    for index in range(count):
        offset, key_hash = struct.unpack_from("<II", data, 24 + index * 8)
        if offset < 24 + count * 8 or offset + 4 > len(data):
            # The observed tables contain one pre-data sentinel record at index 0.
            if index == 0 and offset == 24 + count * 8 - 24:
                continue
            raise FormatError(f"STBL record {index} offset is outside string data")
        length = struct.unpack_from("<I", data, offset)[0]
        if length > len(data) - offset - 4:
            raise FormatError(f"STBL record {index} is truncated")
        raw = data[offset + 4 : offset + 4 + length]
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            raise FormatError(f"STBL record {index} has invalid text encoding") from exc
        output.append(StringRecord(index, key_hash, offset, text))
    return output
