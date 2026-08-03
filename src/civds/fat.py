"""Nintendo DS File Allocation Table parser."""

from dataclasses import dataclass
import struct
from .errors import FormatError


@dataclass(frozen=True)
class FATEntry:
    file_id: int
    start: int
    end: int


def parse_fat(data: bytes, rom_size: int) -> list[FATEntry]:
    if len(data) % 8:
        raise FormatError("truncated FAT record")
    out = []
    for file_id, pos in enumerate(range(0, len(data), 8)):
        start, end = struct.unpack_from("<II", data, pos)
        if start > end or end > rom_size:
            raise FormatError(f"invalid FAT range for file {file_id}")
        out.append(FATEntry(file_id, start, end))
    ordered = sorted((x.start, x.end, x.file_id) for x in out if x.start != x.end)
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            raise FormatError(f"overlapping FAT files {previous[2]} and {current[2]}")
    return out
