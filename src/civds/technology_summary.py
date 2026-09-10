from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.technology import (
    TECH_RECORD_COUNT,
    TECH_RECORD_SIZE,
    TechnologyRecord,
    parse_technology_records,
)


def build_technology_summary(records: tuple[TechnologyRecord, ...]) -> dict[str, object]:
    if len(records) != TECH_RECORD_COUNT:
        raise ValueError(f"expected {TECH_RECORD_COUNT} technology records, got {len(records)}")

    technologies: list[dict[str, object]] = []
    for record in records:
        technology = asdict(record)
        technology["prerequisite_technology_names"] = [
            None if technology_id < 0 else _name_by_id(records, technology_id)
            for technology_id in record.prerequisite_technology_ids
        ]
        technologies.append(technology)

    return {
        "format_version": 1,
        "record_count": TECH_RECORD_COUNT,
        "record_size": TECH_RECORD_SIZE,
        "technologies": technologies,
    }


def _name_by_id(records: tuple[TechnologyRecord, ...], technology_id: int) -> str | None:
    for record in records:
        if record.index == technology_id:
            return record.name
    return None


def write_technology_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_technology_summary(parse_technology_records(arm9))
    write_json_atomic(output, payload)
    return output
