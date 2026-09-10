from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from nds_disassembly_toolkit.nds.header import NdsHeader
from nds_disassembly_toolkit.profile import load_profile, validate_rom
from nds_disassembly_toolkit.workspace.manifest import write_json_atomic

from civds.combat import COMBAT_CONSTANTS, read_combat_constant_value


def build_combat_summary(blob: bytes) -> dict[str, object]:
    constants = []
    for constant in COMBAT_CONSTANTS:
        entry = asdict(constant)
        entry["current_value"] = read_combat_constant_value(blob, constant)
        constants.append(entry)

    return {
        "format_version": 1,
        "constant_count": len(COMBAT_CONSTANTS),
        "constants": constants,
    }


def write_combat_summary(rom: Path, profile_path: Path, output: Path) -> Path:
    profile = load_profile(profile_path)
    validate_rom(rom, profile)

    data = rom.read_bytes()
    header = NdsHeader.from_bytes(data)
    arm9_end = header.arm9_offset + header.arm9_size
    if arm9_end > len(data):
        raise ValueError("ARM9 range extends beyond the ROM")

    arm9 = data[header.arm9_offset:arm9_end]
    payload = build_combat_summary(arm9)
    write_json_atomic(output, payload)
    return output
