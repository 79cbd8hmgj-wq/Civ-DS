from __future__ import annotations

import pytest

from civds import units
from tests.test_units import _text_slot, _unit_record


def _records_with_warrior() -> tuple[units.UnitRecord, ...]:
    prefix = b"header bytes\0" + b"\0" * 73
    encoded = []
    for index in range(units.UNIT_RECORD_COUNT):
        if index == 0:
            encoded.append(_unit_record("Settlers"))
        elif index == 6:
            encoded.append(
                _unit_record(
                    "Warrior",
                    attack=1,
                    defense=1,
                    movement=1,
                    production_cost_quanta=2,
                    unlock_technology_id=-1,
                    obsolete_technology_id_1=6,
                    obsolete_technology_id_2=17,
                    flags=0x00040120,
                )
            )
        else:
            encoded.append(_unit_record(f"Unit {index}"))
    blob = prefix + b"".join(encoded) + _text_slot("Pyramids of Egypt") + b"tail"
    return units.parse_unit_records(blob)


def test_build_unit_patch_set_guards_recovered_fields_with_exact_bytes() -> None:
    records = _records_with_warrior()
    warrior = records[6]

    patch_set = units.build_unit_patch_set(
        records,
        unit_name="Warrior",
        profile_id="synthetic_units",
        attack=3,
        defense=4,
        movement=2,
        fuel_turn_limit=5,
        production_cost=20,
        unlock_technology_id=6,
        obsolete_technology_id_1=17,
        obsolete_technology_id_2=-1,
    )

    assert patch_set == {
        "format_version": 1,
        "profile_id": "synthetic_units",
        "patches": [
            {
                "id": "unit-006-attack",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x40,
                "expected": "01",
                "replacement": "03",
                "rationale": "Set Warrior attack from 1 to 3",
            },
            {
                "id": "unit-006-defense",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x41,
                "expected": "01",
                "replacement": "04",
                "rationale": "Set Warrior defense from 1 to 4",
            },
            {
                "id": "unit-006-movement",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x42,
                "expected": "01",
                "replacement": "02",
                "rationale": "Set Warrior movement from 1 to 2",
            },
            {
                "id": "unit-006-fuel-turn-limit",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x43,
                "expected": "00",
                "replacement": "05",
                "rationale": "Set Warrior fuel/turn limit from 0 to 5",
            },
            {
                "id": "unit-006-production-cost",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x44,
                "expected": "02",
                "replacement": "04",
                "rationale": "Set Warrior production cost from 10 to 20",
            },
            {
                "id": "unit-006-unlock-technology",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x4A,
                "expected": "ffff",
                "replacement": "0600",
                "rationale": "Set Warrior unlock technology from none (-1) to Iron Working (6)",
            },
            {
                "id": "unit-006-obsolete-technology-1",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x4C,
                "expected": "0600",
                "replacement": "1100",
                "rationale": (
                    "Set Warrior obsolete technology 1 from Iron Working (6) "
                    "to Feudalism (17)"
                ),
            },
            {
                "id": "unit-006-obsolete-technology-2",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x4E,
                "expected": "1100",
                "replacement": "ffff",
                "rationale": "Set Warrior obsolete technology 2 from Feudalism (17) to none (-1)",
            },
        ],
    }


def test_build_unit_patch_set_rejects_non_quantized_production_cost() -> None:
    records = _records_with_warrior()

    with pytest.raises(ValueError, match="multiple of 5"):
        units.build_unit_patch_set(
            records,
            unit_name="Warrior",
            profile_id="synthetic_units",
            production_cost=21,
        )


def test_build_unit_patch_set_rejects_values_outside_descriptor_byte() -> None:
    records = _records_with_warrior()

    with pytest.raises(ValueError, match=r"attack.*signed byte"):
        units.build_unit_patch_set(
            records,
            unit_name="Warrior",
            profile_id="synthetic_units",
            attack=128,
        )


def test_build_unit_patch_set_rejects_unknown_technology_ids() -> None:
    records = _records_with_warrior()

    with pytest.raises(ValueError, match="technology id"):
        units.build_unit_patch_set(
            records,
            unit_name="Warrior",
            profile_id="synthetic_units",
            unlock_technology_id=len(units.TECHNOLOGY_NAMES),
        )


def test_build_unit_patch_set_rejects_empty_edit_request() -> None:
    records = _records_with_warrior()

    with pytest.raises(ValueError, match="no unit fields"):
        units.build_unit_patch_set(
            records,
            unit_name="Warrior",
            profile_id="synthetic_units",
        )
