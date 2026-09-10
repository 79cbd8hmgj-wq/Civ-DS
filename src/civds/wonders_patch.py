from __future__ import annotations

from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.wonders import build_wonder_patch_set, parse_wonder_records


def write_wonder_patch_manifest(
    rom: Path,
    profile_path: Path,
    output: Path,
    *,
    wonder_name: str,
    production_cost: int | None = None,
    prerequisite_technology_id: int | None = None,
    description: str | None = None,
) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    records = parse_wonder_records(arm9)
    payload = build_wonder_patch_set(
        records,
        wonder_name=wonder_name,
        profile_id=profile.id,
        production_cost=production_cost,
        prerequisite_technology_id=prerequisite_technology_id,
        description=description,
    )
    write_json_atomic(output, payload)
    return output
