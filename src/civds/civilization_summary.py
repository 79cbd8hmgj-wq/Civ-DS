from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.civilization import (
    CIVILIZATION_COUNT,
    CivilizationRecord,
    parse_civilization_records,
)


def build_civilization_summary(records: tuple[CivilizationRecord, ...]) -> dict[str, object]:
    if len(records) != CIVILIZATION_COUNT:
        raise ValueError(
            f"expected {CIVILIZATION_COUNT} civilization records, got {len(records)}"
        )

    return {
        "format_version": 1,
        "record_count": CIVILIZATION_COUNT,
        "civilizations": [asdict(record) for record in records],
    }


def write_civilization_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    records = parse_civilization_records(arm9, arm9_ram_address=header.arm9_ram_address)
    payload = build_civilization_summary(records)
    write_json_atomic(output, payload)
    return output
