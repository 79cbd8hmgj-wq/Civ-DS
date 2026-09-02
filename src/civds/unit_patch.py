from __future__ import annotations

from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.units import build_unit_patch_set, parse_unit_records


def write_unit_patch_manifest(
    rom: Path,
    profile_path: Path,
    output: Path,
    *,
    unit_name: str,
    attack: int | None = None,
    defense: int | None = None,
    movement: int | None = None,
    production_cost: int | None = None,
) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    records = parse_unit_records(arm9)
    payload = build_unit_patch_set(
        records,
        unit_name=unit_name,
        profile_id=profile.id,
        attack=attack,
        defense=defense,
        movement=movement,
        production_cost=production_cost,
    )
    write_json_atomic(output, payload)
    return output
