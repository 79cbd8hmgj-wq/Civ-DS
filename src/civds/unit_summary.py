from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.units import (
    UNIT_RECORD_COUNT,
    UNIT_RECORD_SIZE,
    UnitRecord,
    parse_unit_records,
    technology_name,
)


def build_unit_summary(records: tuple[UnitRecord, ...]) -> dict[str, object]:
    if len(records) != UNIT_RECORD_COUNT:
        raise ValueError(f"expected {UNIT_RECORD_COUNT} unit records, got {len(records)}")

    units: list[dict[str, object]] = []
    for record in records:
        unit = asdict(record)
        unit["production_cost"] = record.production_cost
        unit["formation_size"] = record.formation_size
        unit["is_settler"] = record.is_settler
        unit["is_naval"] = record.is_naval
        unit["is_air"] = record.is_air
        unit["can_carry_units"] = record.can_carry_units
        unit["is_great_person"] = record.is_great_person
        unit["is_great_general"] = record.is_great_general
        unit["is_spy"] = record.is_spy
        unit["is_icbm"] = record.is_icbm
        unit["unlock_technology_name"] = technology_name(record.unlock_technology_id)
        unit["obsolete_technology_name_1"] = technology_name(
            record.obsolete_technology_id_1
        )
        unit["obsolete_technology_name_2"] = technology_name(
            record.obsolete_technology_id_2
        )
        units.append(unit)

    return {
        "format_version": 1,
        "record_count": UNIT_RECORD_COUNT,
        "record_size": UNIT_RECORD_SIZE,
        "units": units,
    }


def write_unit_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_unit_summary(parse_unit_records(arm9))
    write_json_atomic(output, payload)
    return output
