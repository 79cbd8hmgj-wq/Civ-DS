from __future__ import annotations

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
        production_cost=20,
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
                "id": "unit-006-production-cost",
                "type": "binary_replace",
                "target": "arm9",
                "offset": warrior.offset + 0x44,
                "expected": "02",
                "replacement": "04",
                "rationale": "Set Warrior production cost from 10 to 20",
            },
        ],
    }
