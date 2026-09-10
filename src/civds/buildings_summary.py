from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.buildings import (
    BUILDING_RECORD_COUNT,
    BUILDING_RECORD_SIZE,
    BuildingRecord,
    parse_building_records,
)
from civds.units import technology_name


def build_building_summary(records: tuple[BuildingRecord, ...]) -> dict[str, object]:
    if len(records) != BUILDING_RECORD_COUNT:
        raise ValueError(f"expected {BUILDING_RECORD_COUNT} building records, got {len(records)}")

    buildings: list[dict[str, object]] = []
    for record in records:
        building = asdict(record)
        building["production_cost"] = record.production_cost
        building["prerequisite_technology_name"] = technology_name(
            record.prerequisite_technology_id
        )
        buildings.append(building)

    return {
        "format_version": 1,
        "record_count": BUILDING_RECORD_COUNT,
        "record_size": BUILDING_RECORD_SIZE,
        "buildings": buildings,
    }


def write_building_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_building_summary(parse_building_records(arm9))
    write_json_atomic(output, payload)
    return output
