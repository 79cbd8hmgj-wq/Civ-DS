from __future__ import annotations

import struct
from dataclasses import dataclass

UNIT_RECORD_SIZE = 0x94
UNIT_RECORD_COUNT = 38
UNIT_FLAG_SETTLER = 0x00000001
UNIT_FLAG_NAVAL = 0x00000002
UNIT_FLAG_AIR = 0x00000004
UNIT_FLAG_GREAT_PERSON = 0x00000080
UNIT_FLAG_GREAT_GENERAL = 0x00008000
UNIT_FLAG_SPY = 0x00010000
UNIT_FLAG_ICBM = 0x00020000
_UNIT_START_ANCHOR = b"Settlers\0"
_UNIT_END_ANCHOR = b"Pyramids of Egypt\0"

TECHNOLOGY_NAMES = (
    "never",
    "Alphabet",
    "Bronze Working",
    "Ceremonial Burial",
    "Horseback Riding",
    "Pottery",
    "Iron Working",
    "Masonry",
    "Writing",
    "Code of Laws",
    "Construction",
    "Irrigation",
    "Literacy",
    "Mathematics",
    "Currency",
    "Democracy",
    "Engineering",
    "Feudalism",
    "Monarchy",
    "Religion",
    "Banking",
    "University",
    "Invention",
    "Navigation",
    "Gunpowder",
    "Metallurgy",
    "Printing Press",
    "Steam Power",
    "Combustion",
    "Electricity",
    "Industrialization",
    "Railroad",
    "Communism",
    "Flight",
    "Mass Production",
    "Steel",
    "The Corporation",
    "Atomic Theory",
    "Electronics",
    "Mass Media",
    "The Automobile",
    "Advanced Flight",
    "Nuclear Power",
    "Networking",
    "Space Flight",
    "Globalization",
    "Superconductor",
    "Future Technology",
)


def technology_name(technology_id: int) -> str | None:
    if technology_id == -1:
        return None
    if not 0 <= technology_id < len(TECHNOLOGY_NAMES):
        raise ValueError(f"technology id {technology_id} is outside the recovered runtime catalog")
    return TECHNOLOGY_NAMES[technology_id]


@dataclass(frozen=True)
class UnitRecord:
    index: int
    offset: int
    name: str
    model_name: str
    model_alt_a: str
    model_alt_b: str
    attack: int
    defense: int
    movement: int
    fuel_turn_limit: int
    production_cost_quanta: int
    unknown_0x45: int
    unknown_0x46: int
    unknown_0x47: int
    formation_mask: int
    reserved_0x49: int
    unlock_technology_id: int
    obsolete_technology_id_1: int
    obsolete_technology_id_2: int
    flags: int

    @property
    def production_cost(self) -> int:
        return self.production_cost_quanta * 5

    @property
    def formation_size(self) -> int:
        return self.formation_mask.bit_count()

    @property
    def is_settler(self) -> bool:
        return bool(self.flags & UNIT_FLAG_SETTLER)

    @property
    def is_naval(self) -> bool:
        return bool(self.flags & UNIT_FLAG_NAVAL)

    @property
    def is_air(self) -> bool:
        return bool(self.flags & UNIT_FLAG_AIR)

    @property
    def is_great_person(self) -> bool:
        return bool(self.flags & UNIT_FLAG_GREAT_PERSON)

    @property
    def is_great_general(self) -> bool:
        return bool(self.flags & UNIT_FLAG_GREAT_GENERAL)

    @property
    def is_spy(self) -> bool:
        return bool(self.flags & UNIT_FLAG_SPY)

    @property
    def is_icbm(self) -> bool:
        return bool(self.flags & UNIT_FLAG_ICBM)


def _unique_offset(blob: bytes, needle: bytes, label: str) -> int:
    first = blob.find(needle)
    if first < 0:
        raise ValueError(f"{label} anchor not found")
    if blob.find(needle, first + 1) >= 0:
        raise ValueError(f"{label} anchor is not unique")
    return first


def _decode_slot(slot: bytes) -> str:
    if len(slot) != 32:
        raise ValueError("unit text slot must be exactly 32 bytes")
    terminator = slot.find(b"\0")
    if terminator < 0:
        raise ValueError("unit text slot is not NUL-terminated")
    raw = slot[:terminator]
    if any(byte < 0x20 or byte > 0x7E for byte in raw):
        raise ValueError("unit text slot contains non-printable ASCII")
    if any(slot[terminator + 1 :]):
        raise ValueError("unit text slot contains nonzero padding")
    return raw.decode("ascii")


def parse_unit_records(blob: bytes) -> tuple[UnitRecord, ...]:
    start = _unique_offset(blob, _UNIT_START_ANCHOR, "Settlers")
    end = _unique_offset(blob, _UNIT_END_ANCHOR, "Pyramids of Egypt")
    expected_end = start + UNIT_RECORD_COUNT * UNIT_RECORD_SIZE
    if end != expected_end:
        raise ValueError(
            "unit descriptor table boundary does not match 38 x 148-byte records"
        )

    records: list[UnitRecord] = []
    for index in range(UNIT_RECORD_COUNT):
        offset = start + index * UNIT_RECORD_SIZE
        raw = blob[offset : offset + UNIT_RECORD_SIZE]
        if len(raw) != UNIT_RECORD_SIZE:
            raise ValueError(f"unit record {index} is truncated")

        (
            attack,
            defense,
            movement,
            fuel_turn_limit,
            production_cost_quanta,
            unknown_0x45,
            unknown_0x46,
            unknown_0x47,
            formation_mask,
            reserved_0x49,
            unlock_technology_id,
            obsolete_technology_id_1,
            obsolete_technology_id_2,
            flags,
        ) = struct.unpack_from("<bbbbbbbbBBhhhI", raw, 0x40)

        records.append(
            UnitRecord(
                index=index,
                offset=offset,
                name=_decode_slot(raw[0x00:0x20]),
                model_name=_decode_slot(raw[0x20:0x40]),
                model_alt_a=_decode_slot(raw[0x54:0x74]),
                model_alt_b=_decode_slot(raw[0x74:0x94]),
                attack=attack,
                defense=defense,
                movement=movement,
                fuel_turn_limit=fuel_turn_limit,
                production_cost_quanta=production_cost_quanta,
                unknown_0x45=unknown_0x45,
                unknown_0x46=unknown_0x46,
                unknown_0x47=unknown_0x47,
                formation_mask=formation_mask,
                reserved_0x49=reserved_0x49,
                unlock_technology_id=unlock_technology_id,
                obsolete_technology_id_1=obsolete_technology_id_1,
                obsolete_technology_id_2=obsolete_technology_id_2,
                flags=flags,
            )
        )

    return tuple(records)
