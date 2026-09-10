from __future__ import annotations

from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.combat import build_combat_patch_set


def write_combat_patch_manifest(
    rom: Path,
    profile_path: Path,
    output: Path,
    *,
    values: dict[str, int],
) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_combat_patch_set(arm9, profile_id=profile.id, values=values)
    write_json_atomic(output, payload)
    return output
