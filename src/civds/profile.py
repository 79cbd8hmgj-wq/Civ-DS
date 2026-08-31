from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nds_disassembly_toolkit.inspection import inspect_rom


def build_profile_payload(rom: Path, *, profile_id: str) -> dict[str, Any]:
    """Build an exact-ROM toolkit profile from a structurally valid NDS ROM."""
    inspection = inspect_rom(rom)
    identity = inspection.identity
    header = inspection.header
    return {
        "id": profile_id,
        "sha256": identity.sha256,
        "size": identity.size,
        "title": identity.title,
        "game_code": identity.game_code,
        "maker_code": identity.maker_code,
        "revision": identity.revision,
        "expected": {
            "arm9_offset": header.arm9_offset,
            "arm9_ram_address": header.arm9_ram_address,
            "arm9_size": header.arm9_size,
            "arm7_offset": header.arm7_offset,
            "arm7_ram_address": header.arm7_ram_address,
            "arm7_size": header.arm7_size,
            "fnt_offset": header.fnt_offset,
            "fnt_size": header.fnt_size,
            "fat_offset": header.fat_offset,
            "fat_size": header.fat_size,
            "arm9_overlay_offset": header.arm9_overlay_offset,
            "arm9_overlay_size": header.arm9_overlay_size,
            "arm7_overlay_offset": header.arm7_overlay_offset,
            "arm7_overlay_size": header.arm7_overlay_size,
            "nitrofs_file_count": len(inspection.fat),
            "directory_count": len(inspection.fnt.directories),
            "arm9_overlay_count": len(inspection.arm9_overlays),
            "arm7_overlay_count": len(inspection.arm7_overlays),
        },
    }


def write_profile(rom: Path, output: Path, *, profile_id: str) -> Path:
    """Write a deterministic exact-ROM profile atomically."""
    payload = build_profile_payload(rom, profile_id=profile_id)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return output
