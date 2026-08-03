"""Bounded ROM inspection orchestration."""

from pathlib import Path
from dataclasses import asdict
from .fat import parse_fat
from .fnt import parse_fnt
from .nds_header import read_header
from .overlays import parse_overlays


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
    fat = parse_fat(_read(path, h.fat.rom_offset, h.fat.size), h.rom_size)
    files = parse_fnt(_read(path, h.fnt.rom_offset, h.fnt.size), len(fat))
    ovs = []
    for processor, table in (("arm9", h.arm9_overlay_table), ("arm7", h.arm7_overlay_table)):
        for ov in parse_overlays(_read(path, table.rom_offset, table.size), len(fat)):
            d = asdict(ov)
            d["processor"] = processor
            d["rom_offset"] = fat[ov.file_id].start
            ovs.append(d)
    header = h.to_dict()
    header["file_count"] = len(fat)
    header["named_file_count"] = len(files)
    header["overlay_count"] = len(ovs)
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
