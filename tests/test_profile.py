from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from civds.profile import build_profile_payload, write_profile


def _make_structural_rom(path: Path) -> bytes:
    rom = bytearray(b"\xff" * 0x2000)
    rom[0x00:0x0C] = b"SYNTH NDS\x00\x00\x00"
    rom[0x0C:0x10] = b"TST0"
    rom[0x10:0x12] = b"00"
    rom[0x1E] = 1
    struct.pack_into("<III", rom, 0x20, 0x200, 0x02000000, 0x02000000)
    struct.pack_into("<I", rom, 0x2C, 4)
    struct.pack_into("<III", rom, 0x30, 0x204, 0x02380000, 0x02380000)
    struct.pack_into("<I", rom, 0x3C, 4)

    fnt = bytearray(struct.pack("<IHH", 8, 1, 1))
    fnt.extend(bytes([5]) + b"a.bin")
    fnt.extend(bytes([5]) + b"b.bin")
    fnt.append(0)
    rom[0x400 : 0x400 + len(fnt)] = fnt
    struct.pack_into("<II", rom, 0x40, 0x400, len(fnt))
    struct.pack_into("<II", rom, 0x48, 0x500, 24)
    struct.pack_into("<II", rom, 0x50, 0x300, 32)
    struct.pack_into("<II", rom, 0x58, 0, 0)
    struct.pack_into("<I", rom, 0x80, len(rom))

    rom[0x600:0x604] = b"OVER"
    rom[0x800:0x805] = b"FILE1"
    rom[0xA00:0xA05] = b"FILE2"
    struct.pack_into("<II", rom, 0x500, 0x600, 0x604)
    struct.pack_into("<II", rom, 0x508, 0x800, 0x805)
    struct.pack_into("<II", rom, 0x510, 0xA00, 0xA05)
    struct.pack_into("<8I", rom, 0x300, 0, 0x02200000, 4, 0, 0, 0, 0, 0)
    rom[0x200:0x204] = b"ARM9"
    rom[0x204:0x208] = b"ARM7"
    path.write_bytes(rom)
    return bytes(rom)


def test_build_profile_payload_records_identity_and_layout(tmp_path: Path) -> None:
    rom_path = tmp_path / "synthetic.nds"
    data = _make_structural_rom(rom_path)

    payload = build_profile_payload(rom_path, profile_id="synthetic_rev1")

    assert payload["id"] == "synthetic_rev1"
    assert payload["sha256"] == hashlib.sha256(data).hexdigest()
    assert payload["size"] == len(data)
    assert payload["title"] == "SYNTH NDS"
    assert payload["game_code"] == "TST0"
    assert payload["maker_code"] == "00"
    assert payload["revision"] == 1
    assert payload["expected"] == {
        "arm9_offset": 0x200,
        "arm9_ram_address": 0x02000000,
        "arm9_size": 4,
        "arm7_offset": 0x204,
        "arm7_ram_address": 0x02380000,
        "arm7_size": 4,
        "fnt_offset": 0x400,
        "fnt_size": 21,
        "fat_offset": 0x500,
        "fat_size": 24,
        "arm9_overlay_offset": 0x300,
        "arm9_overlay_size": 32,
        "arm7_overlay_offset": 0,
        "arm7_overlay_size": 0,
        "nitrofs_file_count": 3,
        "directory_count": 1,
        "arm9_overlay_count": 1,
        "arm7_overlay_count": 0,
    }


def test_write_profile_is_deterministic_and_creates_parent(tmp_path: Path) -> None:
    rom_path = tmp_path / "synthetic.nds"
    _make_structural_rom(rom_path)
    output = tmp_path / "profiles" / "game.json"

    write_profile(rom_path, output, profile_id="synthetic_rev1")
    first = output.read_bytes()
    write_profile(rom_path, output, profile_id="synthetic_rev1")

    assert output.read_bytes() == first
    assert json.loads(first)["id"] == "synthetic_rev1"
    assert first.endswith(b"\n")
