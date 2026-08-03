"""Strict ARM overlay table records."""

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


def parse_overlays(data: bytes, file_extents: int | list[int]) -> list[Overlay]:
    if len(data) % 32:
        raise FormatError("truncated overlay record")
    extents = file_extents if isinstance(file_extents, list) else [0] * file_extents
    output: list[Overlay] = []
    ids: set[int] = set()
    for position in range(0, len(data), 32):
        row = Overlay(*struct.unpack_from("<8I", data, position))
        if row.overlay_id in ids:
            raise FormatError(f"duplicate overlay ID {row.overlay_id}")
        if row.file_id >= len(extents):
            raise FormatError(f"overlay {row.overlay_id} has impossible file ID")
        runtime_end = row.load_address + row.static_size
        bss_end = runtime_end + row.bss_size
        if runtime_end > 0x1_0000_0000 or bss_end > 0x1_0000_0000:
            raise FormatError(f"overlay {row.overlay_id} runtime range overflows")
        if row.static_init_start or row.static_init_end:
            if not (
                row.load_address <= row.static_init_start <= row.static_init_end <= runtime_end
            ):
                raise FormatError(
                    f"overlay {row.overlay_id} initializer range is outside static data"
                )
        extent = extents[row.file_id]
        if row.is_compressed:
            if row.compressed_size == 0 or (extent and row.compressed_size > extent):
                raise FormatError(f"overlay {row.overlay_id} compressed size exceeds FAT extent")
        elif extent and row.static_size > extent:
            raise FormatError(f"overlay {row.overlay_id} static size exceeds FAT extent")
        ids.add(row.overlay_id)
        output.append(row)
    return output
