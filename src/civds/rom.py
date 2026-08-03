"""Bounded ROM inspection orchestration."""

from pathlib import Path
from dataclasses import asdict
from .errors import FormatError
from .fat import parse_fat
from .fnt import parse_fnt
from .nds_header import HEADER_SIZE, read_header
from .overlays import parse_overlays

BANNER_EXTENTS = {1: 0x840, 2: 0x940, 3: 0xA40, 0x103: 0x23C0}


def _read(path: Path, offset: int, size: int) -> bytes:
    with path.open("rb") as stream:
        stream.seek(offset)
        data = stream.read(size)
    if len(data) != size:
        raise OSError("short read after validated range")
    return data


def inspect(
    path: Path,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    h = read_header(path)
    banner_prefix = _read(path, h.banner_offset, 2)
    banner_version = int.from_bytes(banner_prefix, "little")
    try:
        banner_extent = BANNER_EXTENTS[banner_version]
    except KeyError as exc:
        raise FormatError(f"unsupported banner version 0x{banner_version:x}") from exc
    if h.banner_offset < HEADER_SIZE or banner_extent > h.rom_size - h.banner_offset:
        raise FormatError("banner range exceeds ROM")
    fat = parse_fat(_read(path, h.fat.rom_offset, h.fat.size), h.rom_size)
    structural = [
        (0, HEADER_SIZE, "header"),
        (h.arm9.rom_offset, h.arm9.rom_offset + h.arm9.size, "arm9"),
        (h.arm7.rom_offset, h.arm7.rom_offset + h.arm7.size, "arm7"),
        (h.fnt.rom_offset, h.fnt.rom_offset + h.fnt.size, "fnt"),
        (h.fat.rom_offset, h.fat.rom_offset + h.fat.size, "fat"),
        (h.banner_offset, h.banner_offset + banner_extent, "banner"),
    ]
    for name, table in (
        ("arm9 overlay table", h.arm9_overlay_table),
        ("arm7 overlay table", h.arm7_overlay_table),
    ):
        if table.size:
            structural.append((table.rom_offset, table.rom_offset + table.size, name))
    ordered = sorted(structural)
    for previous, current in zip(ordered, ordered[1:]):
        if current[0] < previous[1]:
            raise FormatError(f"core ROM regions overlap: {previous[2]} and {current[2]}")
    for entry in fat:
        for start, end, name in structural:
            if entry.start < end and start < entry.end:
                raise FormatError(
                    f"FAT file {entry.file_id} conflicts with structural region {name}"
                )
    files = parse_fnt(_read(path, h.fnt.rom_offset, h.fnt.size), len(fat))
    ovs = []
    for processor, table in (("arm9", h.arm9_overlay_table), ("arm7", h.arm7_overlay_table)):
        extents = [entry.end - entry.start for entry in fat]
        for ov in parse_overlays(_read(path, table.rom_offset, table.size), extents):
            d = asdict(ov)
            d["processor"] = processor
            d["rom_offset"] = fat[ov.file_id].start
            ovs.append(d)
    header = h.to_dict()
    header["file_count"] = len(fat)
    header["named_file_count"] = len(files)
    header["overlay_count"] = len(ovs)
    header["banner_version"] = banner_version
    header["banner_extent"] = banner_extent
    header["secure_area_crc_policy"] = "recorded; not recomputed over encrypted on-ROM secure area"
    return (
        header,
        [
            asdict(x)
            | {
                "rom_offset": fat[x.file_id].start,
                "size": fat[x.file_id].end - fat[x.file_id].start,
            }
            for x in files
        ],
        ovs,
    )
