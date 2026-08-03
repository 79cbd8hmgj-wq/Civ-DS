"""ARM overlay table records."""

from dataclasses import dataclass
import struct
from .errors import FormatError


@dataclass(frozen=True)
class Overlay:
    overlay_id: int
    load_address: int
    static_size: int
    bss_size: int
    static_init_start: int
    static_init_end: int
    file_id: int
    flags: int

    @property
    def compressed_size(self) -> int:
        return self.flags & 0x00FFFFFF

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & 0x01000000)


def parse_overlays(data: bytes, file_count: int) -> list[Overlay]:
    if len(data) % 32:
        raise FormatError("truncated overlay record")
    out = []
    ids = set()
    for pos in range(0, len(data), 32):
        row = Overlay(*struct.unpack_from("<8I", data, pos))
        if row.overlay_id in ids:
            raise FormatError(f"duplicate overlay ID {row.overlay_id}")
        if row.file_id >= file_count:
            raise FormatError(f"overlay {row.overlay_id} has impossible file ID")
        if row.static_init_start > row.static_init_end:
            raise FormatError("reversed static initializer range")
        ids.add(row.overlay_id)
        out.append(row)
    return out
