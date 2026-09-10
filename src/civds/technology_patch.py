from __future__ import annotations

from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.technology import build_technology_patch_set, parse_technology_records


def write_technology_patch_manifest(
    rom: Path,
    profile_path: Path,
    output: Path,
    *,
    technology_name: str,
    prerequisite_technology_id_0: int | None = None,
    prerequisite_technology_id_1: int | None = None,
    prerequisite_technology_id_2: int | None = None,
    effect: str | None = None,
) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    records = parse_technology_records(arm9)
    payload = build_technology_patch_set(
        records,
        technology_name=technology_name,
        profile_id=profile.id,
        prerequisite_technology_ids=(
            prerequisite_technology_id_0,
            prerequisite_technology_id_1,
            prerequisite_technology_id_2,
        ),
        effect=effect,
    )
    write_json_atomic(output, payload)
    return output
