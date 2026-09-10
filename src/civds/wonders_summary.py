from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.units import technology_name
from civds.wonders import (
    WONDER_RECORD_COUNT,
    WONDER_RECORD_SIZE,
    WonderRecord,
    parse_wonder_records,
)


def build_wonder_summary(records: tuple[WonderRecord, ...]) -> dict[str, object]:
    if len(records) != WONDER_RECORD_COUNT:
        raise ValueError(f"expected {WONDER_RECORD_COUNT} wonder records, got {len(records)}")

    wonders: list[dict[str, object]] = []
    for record in records:
        wonder = asdict(record)
        wonder["production_cost"] = record.production_cost
        wonder["prerequisite_technology_name"] = technology_name(record.prerequisite_technology_id)
        wonders.append(wonder)

    return {
        "format_version": 1,
        "record_count": WONDER_RECORD_COUNT,
        "record_size": WONDER_RECORD_SIZE,
        "wonders": wonders,
    }


def write_wonder_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_wonder_summary(parse_wonder_records(arm9))
    write_json_atomic(output, payload)
    return output
