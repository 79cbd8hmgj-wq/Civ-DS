from __future__ import annotations

from pathlib import Path

import pytest

from civds.cli import DEFAULT_PROFILE, build_parser, main


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
