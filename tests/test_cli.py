from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from civds.cli import DEFAULT_PROFILE, build_parser, main
from civds.profile import write_profile
from civds.units import UNIT_RECORD_COUNT, UNIT_RECORD_SIZE


def test_parser_enforces_civrev_profile_for_rom_writes() -> None:
    parser = build_parser()

    inspect_args = parser.parse_args(["inspect", "game.nds"])
    assert inspect_args.profile == DEFAULT_PROFILE
    assert inspect_args.require_supported is True

    relaxed = parser.parse_args(["inspect", "game.nds", "--allow-unsupported"])
    assert relaxed.require_supported is False

    extract_args = parser.parse_args(["extract", "game.nds", "work/game"])
    assert extract_args.profile == DEFAULT_PROFILE
    assert extract_args.require_supported is True

    with pytest.raises(SystemExit):
        parser.parse_args(["extract", "game.nds", "work/game", "--allow-unsupported"])


def test_parser_pins_profile_for_asset_disassembly_and_source_patch() -> None:
    parser = build_parser()

    assets_args = parser.parse_args(["assets", "inventory", "game.nds"])
    assert assets_args.profile == DEFAULT_PROFILE
    assert assets_args.require_supported is True

    disasm_args = parser.parse_args(["disasm", "overlay-map", "game.nds"])
    assert disasm_args.profile == DEFAULT_PROFILE
    assert disasm_args.require_supported is True

    patch_args = parser.parse_args(["source-patch", "build", "work/game", "patch.json"])
    assert patch_args.profile == DEFAULT_PROFILE


def test_profile_create_command_writes_profile(tmp_path: Path) -> None:
    from tests.test_profile import _make_structural_rom

    rom = tmp_path / "game.nds"
    _make_structural_rom(rom)
    output = tmp_path / "profiles" / "game.json"

    result = main(
        [
            "profile",
            "create",
            str(rom),
            "--id",
            "synthetic_rev1",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert output.exists()


def _make_unit_summary_rom(path: Path) -> None:
    from tests.test_profile import _make_structural_rom
    from tests.test_units import _text_slot, _unit_record

    rom = bytearray(_make_structural_rom(path))
    rom.extend(b"\xff" * (0x4000 - len(rom)))

    records = []
    for index in range(UNIT_RECORD_COUNT):
        if index == 0:
            records.append(_unit_record("Settlers", model="settler_rom"))
        elif index == 6:
            records.append(
                _unit_record(
                    "Warrior",
                    model="Swordsman",
                    attack=1,
                    defense=1,
                    movement=1,
                    production_cost_quanta=2,
                    formation_mask=7,
                    unlock_technology_id=-1,
                    obsolete_technology_id_1=6,
                    obsolete_technology_id_2=17,
                    flags=0x00040120,
                )
            )
        else:
            records.append(_unit_record(f"Unit {index}"))

    arm9 = b"".join(records) + _text_slot("Pyramids of Egypt")
    arm9_offset = 0x1000
    assert len(arm9) == UNIT_RECORD_COUNT * UNIT_RECORD_SIZE + 32
    rom[arm9_offset : arm9_offset + len(arm9)] = arm9
    struct.pack_into("<I", rom, 0x20, arm9_offset)
    struct.pack_into("<I", rom, 0x2C, len(arm9))
    struct.pack_into("<I", rom, 0x80, len(rom))
    path.write_bytes(rom)


def test_units_summarize_validates_profile_and_resolves_technology_names(
    tmp_path: Path,
) -> None:
    rom = tmp_path / "game.nds"
    _make_unit_summary_rom(rom)
    profile = tmp_path / "profile.json"
    write_profile(rom, profile, profile_id="synthetic_units")
    output = tmp_path / "units.json"

    result = main(
        [
            "units",
            "summarize",
            str(rom),
            "--profile",
            str(profile),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["record_count"] == UNIT_RECORD_COUNT
    assert payload["record_size"] == UNIT_RECORD_SIZE
    warrior = payload["units"][6]
    assert warrior["name"] == "Warrior"
    assert warrior["production_cost_quanta"] == 2
    assert warrior["production_cost"] == 10
    assert warrior["formation_mask"] == 7
    assert warrior["formation_size"] == 3
    assert warrior["reserved_0x49"] == 0
    assert warrior["unlock_technology_name"] is None
    assert warrior["obsolete_technology_name_1"] == "Iron Working"
    assert warrior["obsolete_technology_name_2"] == "Feudalism"
