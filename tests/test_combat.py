from __future__ import annotations

import pytest

from civds.combat import (
    COMBAT_CONSTANTS,
    build_combat_patch_set,
    read_combat_constant_value,
)
from civds.combat_summary import build_combat_summary


def _arm9_blob() -> bytearray:
    size = max(constant.arm9_offset for constant in COMBAT_CONSTANTS) + 0x100
    blob = bytearray(size)
    # AL-condition "mov r1, #imm8" template (0xe3a010xx), rotate=0.
    for constant in COMBAT_CONSTANTS:
        blob[constant.arm9_offset : constant.arm9_offset + 4] = bytes(
            [50, 0x10, 0xA0, 0xE3]
        )
    return blob


def test_read_combat_constant_value_decodes_the_unrotated_immediate() -> None:
    blob = _arm9_blob()
    for constant in COMBAT_CONSTANTS:
        assert read_combat_constant_value(blob, constant) == 50


def test_read_combat_constant_value_rejects_a_rotated_immediate() -> None:
    blob = _arm9_blob()
    constant = COMBAT_CONSTANTS[0]
    # set a nonzero rotate nibble (low nibble of byte 1)
    blob[constant.arm9_offset + 1] = 0x11

    with pytest.raises(ValueError, match="unexpected rotate field"):
        read_combat_constant_value(blob, constant)


def test_build_combat_summary_reports_every_constant_with_its_current_value() -> None:
    blob = _arm9_blob()

    summary = build_combat_summary(bytes(blob))

    assert summary["constant_count"] == len(COMBAT_CONSTANTS)
    constants = summary["constants"]
    assert isinstance(constants, list)
    assert all(entry["current_value"] == 50 for entry in constants)
    names = {entry["name"] for entry in constants}
    assert "fortified-in-city-bonus" in names
    assert "veteran-tier-bonus-attacker" in names


def test_build_combat_patch_set_emits_a_guarded_single_byte_patch() -> None:
    blob = _arm9_blob()
    constant = COMBAT_CONSTANTS[0]

    patch_set = build_combat_patch_set(
        bytes(blob), profile_id="civrev-usa", values={constant.name: 75}
    )

    assert patch_set["profile_id"] == "civrev-usa"
    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["target"] == "arm9"
    assert patch["offset"] == constant.arm9_offset
    assert patch["expected"] == "32"
    assert patch["replacement"] == "4b"


def test_build_combat_patch_set_rejects_an_unknown_constant_name() -> None:
    blob = _arm9_blob()

    with pytest.raises(ValueError, match="unknown combat constant"):
        build_combat_patch_set(bytes(blob), profile_id="civrev-usa", values={"nope": 1})


def test_build_combat_patch_set_rejects_an_out_of_range_value() -> None:
    blob = _arm9_blob()
    constant = COMBAT_CONSTANTS[0]

    with pytest.raises(ValueError, match="must be between 0 and 255"):
        build_combat_patch_set(bytes(blob), profile_id="civrev-usa", values={constant.name: 999})


def test_build_combat_patch_set_requires_at_least_one_value() -> None:
    blob = _arm9_blob()

    with pytest.raises(ValueError, match="no combat constants"):
        build_combat_patch_set(bytes(blob), profile_id="civrev-usa", values={})
