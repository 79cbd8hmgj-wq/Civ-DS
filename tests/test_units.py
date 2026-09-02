from __future__ import annotations

import struct

from civds.units import (
    UNIT_RECORD_COUNT,
    UNIT_RECORD_SIZE,
    parse_unit_records,
    technology_name,
)


def _text_slot(text: str) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= 32:
        raise ValueError("fixture text is too long")
    return encoded + b"\0" + b"\0" * (31 - len(encoded))


def _unit_record(
    name: str,
    *,
    model: str = "model",
    alt_a: str = "model",
    alt_b: str = "model",
    attack: int = 0,
    defense: int = 0,
    movement: int = 0,
    fuel_turn_limit: int = 0,
    production_cost_quanta: int = 0,
    unknown_0x45: int = -1,
    unknown_0x46: int = 0,
    unknown_0x47: int = 0,
    formation_mask: int = 1,
    unknown_0x49: int = 0,
    unlock_technology_id: int = -1,
    obsolete_technology_id_1: int = -1,
    obsolete_technology_id_2: int = -1,
    flags: int = 0,
) -> bytes:
    raw = bytearray(UNIT_RECORD_SIZE)
    raw[0x00:0x20] = _text_slot(name)
    raw[0x20:0x40] = _text_slot(model)
    struct.pack_into(
        "<bbbbbbbbBBhhhI",
        raw,
        0x40,
        attack,
        defense,
        movement,
        fuel_turn_limit,
        production_cost_quanta,
        unknown_0x45,
        unknown_0x46,
        unknown_0x47,
        formation_mask,
        unknown_0x49,
        unlock_technology_id,
        obsolete_technology_id_1,
        obsolete_technology_id_2,
        flags,
    )
    raw[0x54:0x74] = _text_slot(alt_a)
    raw[0x74:0x94] = _text_slot(alt_b)
    return bytes(raw)


def test_parse_unit_records_recovers_confirmed_descriptor_layout() -> None:
    prefix = b"header bytes\0" + b"\0" * 73
    encoded_records = []
    for index in range(UNIT_RECORD_COUNT):
        if index == 0:
            encoded_records.append(
                _unit_record(
                    "Settlers",
                    model="settler_rom",
                    alt_a="Settler_Male",
                    alt_b="Settler_Male",
                    production_cost_quanta=4,
                )
            )
        elif index == 6:
            encoded_records.append(
                _unit_record(
                    "Warrior",
                    model="Swordsman",
                    alt_a="Swordsman",
                    alt_b="Swordsman",
                    attack=1,
                    defense=1,
                    movement=1,
                    production_cost_quanta=2,
                    unknown_0x46=1,
                    unknown_0x47=6,
                    formation_mask=7,
                    unknown_0x49=0,
                    unlock_technology_id=-1,
                    obsolete_technology_id_1=6,
                    obsolete_technology_id_2=17,
                    flags=0x00040120,
                )
            )
        elif index == 20:
            encoded_records.append(
                _unit_record(
                    "Galley",
                    attack=1,
                    defense=1,
                    movement=2,
                    production_cost_quanta=4,
                    formation_mask=1,
                    flags=0x00000012,
                )
            )
        elif index == 26:
            encoded_records.append(
                _unit_record(
                    "Fighter",
                    attack=6,
                    defense=4,
                    movement=8,
                    fuel_turn_limit=2,
                    production_cost_quanta=6,
                    formation_mask=6,
                    unlock_technology_id=33,
                    flags=0x0000200C,
                )
            )
        else:
            encoded_records.append(_unit_record(f"Unit {index}"))

    blob = prefix + b"".join(encoded_records) + _text_slot("Pyramids of Egypt") + b"tail"

    records = parse_unit_records(blob)

    assert len(records) == UNIT_RECORD_COUNT
    assert records[0].offset == len(prefix)
    assert records[0].name == "Settlers"
    assert records[0].model_name == "settler_rom"
    assert records[0].model_alt_a == "Settler_Male"
    assert records[0].model_alt_b == "Settler_Male"
    assert records[0].production_cost_quanta == 4
    assert records[0].production_cost == 20

    warrior = records[6]
    assert warrior.index == 6
    assert warrior.name == "Warrior"
    assert (warrior.attack, warrior.defense, warrior.movement) == (1, 1, 1)
    assert warrior.fuel_turn_limit == 0
    assert warrior.production_cost_quanta == 2
    assert warrior.production_cost == 10
    assert warrior.formation_mask == 7
    assert warrior.formation_size == 3
    assert warrior.unknown_0x49 == 0
    assert warrior.unlock_technology_id == -1
    assert warrior.obsolete_technology_id_1 == 6
    assert warrior.obsolete_technology_id_2 == 17
    assert warrior.flags == 0x00040120
    assert warrior.is_naval is False
    assert warrior.is_air is False

    galley = records[20]
    assert galley.name == "Galley"
    assert galley.is_naval is True
    assert galley.is_air is False

    fighter = records[26]
    assert fighter.name == "Fighter"
    assert fighter.fuel_turn_limit == 2
    assert fighter.production_cost_quanta == 6
    assert fighter.production_cost == 30
    assert fighter.is_naval is False
    assert fighter.is_air is True


def test_technology_name_uses_recovered_runtime_ids() -> None:
    assert technology_name(-1) is None
    assert technology_name(0) == "never"
    assert technology_name(1) == "Alphabet"
    assert technology_name(24) == "Gunpowder"
    assert technology_name(47) == "Future Technology"
