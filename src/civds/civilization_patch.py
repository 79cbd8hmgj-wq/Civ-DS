from __future__ import annotations

from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.civilization import build_civilization_patch_set, parse_civilization_records


def write_civilization_patch_manifest(
    rom: Path,
    profile_path: Path,
    output: Path,
    *,
    leader_name: str,
    new_leader_name: str,
) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    records = parse_civilization_records(arm9, arm9_ram_address=header.arm9_ram_address)
    payload = build_civilization_patch_set(
        records,
        leader_name=leader_name,
        profile_id=profile.id,
        new_leader_name=new_leader_name,
    )
    write_json_atomic(output, payload)
    return output
