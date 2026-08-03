"""Strict parser for the original Nintendo DS header fields used by this project."""

from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
import struct
from typing import cast
from .crc import crc16
from .errors import FormatError

HEADER_SIZE = 0x200


@dataclass(frozen=True)
class Region:
    rom_offset: int
    size: int


@dataclass(frozen=True)
class Program:
    rom_offset: int
    entry_address: int
    load_address: int
    size: int


@dataclass(frozen=True)
class NDSHeader:
    title: str
    game_code: str
    maker_code: str
    unit_code: int
    rom_version: int
    secure_area_checksum: int
    header_checksum: int
    arm9: Program
    arm7: Program
    fnt: Region
    fat: Region
    arm9_overlay_table: Region
    arm7_overlay_table: Region
    banner_offset: int
    rom_size: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _text(data: bytes, start: int, size: int, field: str) -> str:
    try:
        return data[start : start + size].rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError as exc:
        raise FormatError(f"{field} is not ASCII") from exc


def parse_header(data: bytes, rom_size: int) -> NDSHeader:
    if len(data) < HEADER_SIZE:
        raise FormatError("truncated NDS header")
    stored_crc = struct.unpack_from("<H", data, 0x15E)[0]
    actual_crc = crc16(data[:0x15E])
    if stored_crc != actual_crc:
        raise FormatError(
            f"header CRC mismatch: stored 0x{stored_crc:04x}, calculated 0x{actual_crc:04x}"
        )

    def u16(offset: int) -> int:
        return cast(int, struct.unpack_from("<H", data, offset)[0])

    def u32(offset: int) -> int:
        return cast(int, struct.unpack_from("<I", data, offset)[0])

    def region(offset: int) -> Region:
        return Region(u32(offset), u32(offset + 4))

    def program(offset: int) -> Program:
        return Program(u32(offset), u32(offset + 4), u32(offset + 8), u32(offset + 12))

    result = NDSHeader(
        _text(data, 0, 12, "title"),
        _text(data, 12, 4, "game code"),
        _text(data, 16, 2, "maker code"),
        data[18],
        data[30],
        u16(0x6C),
        u16(0x15E),
        program(0x20),
        program(0x30),
        region(0x40),
        region(0x48),
        region(0x50),
        region(0x58),
        u32(0x68),
        rom_size,
    )
    ranges = [
        ("arm9", result.arm9.rom_offset, result.arm9.size),
        ("arm7", result.arm7.rom_offset, result.arm7.size),
        ("fnt", result.fnt.rom_offset, result.fnt.size),
        ("fat", result.fat.rom_offset, result.fat.size),
        (
            "arm9 overlay table",
            result.arm9_overlay_table.rom_offset,
            result.arm9_overlay_table.size,
        ),
        (
            "arm7 overlay table",
            result.arm7_overlay_table.rom_offset,
            result.arm7_overlay_table.size,
        ),
    ]
    for name, offset, size in ranges:
        if size and (offset < HEADER_SIZE or offset > rom_size or size > rom_size - offset):
            raise FormatError(f"{name} range exceeds ROM")
    if result.fat.size % 8:
        raise FormatError("FAT size is not a multiple of 8")
    for name, program_info in (("ARM9", result.arm9), ("ARM7", result.arm7)):
        runtime_end = program_info.load_address + program_info.size
        if runtime_end > 0x1_0000_0000:
            raise FormatError(f"{name} load range overflows 32-bit address space")
        if not (program_info.load_address <= program_info.entry_address < runtime_end):
            raise FormatError(f"{name} entry address is outside its load range")
    for name, table in (("ARM9", result.arm9_overlay_table), ("ARM7", result.arm7_overlay_table)):
        if table.size % 32:
            raise FormatError(f"{name} overlay table size is not a multiple of 32")
    return result


def read_header(path: Path) -> NDSHeader:
    with path.open("rb") as stream:
        data = stream.read(HEADER_SIZE)
    return parse_header(data, path.stat().st_size)
