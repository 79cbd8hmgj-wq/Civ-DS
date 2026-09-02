from __future__ import annotations

import struct
from dataclasses import dataclass

UNIT_RECORD_SIZE = 0x94
UNIT_RECORD_COUNT = 38
UNIT_FLAG_SETTLER = 0x00000001
UNIT_FLAG_NAVAL = 0x00000002
UNIT_FLAG_AIR = 0x00000004
UNIT_FLAG_CAN_CARRY_UNITS = 0x00000010
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
    def can_carry_units(self) -> bool:
        return bool(self.flags & UNIT_FLAG_CAN_CARRY_UNITS)

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


def _signed_byte_hex(value: int, *, label: str) -> str:
    if not -128 <= value <= 127:
        raise ValueError(f"{label} must fit in a signed byte (-128..127)")
    return struct.pack("<b", value).hex()


def _technology_id_hex(value: int) -> str:
    technology_name(value)
    return struct.pack("<h", value).hex()


def _technology_label(value: int) -> str:
    name = technology_name(value)
    if name is None:
        return "none (-1)"
    return f"{name} ({value})"


def build_unit_patch_set(
    records: tuple[UnitRecord, ...],
    *,
    unit_name: str,
    profile_id: str,
    attack: int | None = None,
    defense: int | None = None,
    movement: int | None = None,
    fuel_turn_limit: int | None = None,
    production_cost: int | None = None,
    unlock_technology_id: int | None = None,
    obsolete_technology_id_1: int | None = None,
    obsolete_technology_id_2: int | None = None,
) -> dict[str, object]:
    matches = [record for record in records if record.name == unit_name]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one unit named {unit_name!r}, found {len(matches)}")
    if all(
        value is None
        for value in (
            attack,
            defense,
            movement,
            fuel_turn_limit,
            production_cost,
            unlock_technology_id,
            obsolete_technology_id_1,
            obsolete_technology_id_2,
        )
    ):
        raise ValueError("no unit fields were requested for patching")
    record = matches[0]

    patches: list[dict[str, object]] = []
    if attack is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-attack",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x40,
                "expected": _signed_byte_hex(record.attack, label="current attack"),
                "replacement": _signed_byte_hex(attack, label="attack"),
                "rationale": f"Set {record.name} attack from {record.attack} to {attack}",
            }
        )

    if defense is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-defense",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x41,
                "expected": _signed_byte_hex(record.defense, label="current defense"),
                "replacement": _signed_byte_hex(defense, label="defense"),
                "rationale": f"Set {record.name} defense from {record.defense} to {defense}",
            }
        )

    if movement is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-movement",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x42,
                "expected": _signed_byte_hex(record.movement, label="current movement"),
                "replacement": _signed_byte_hex(movement, label="movement"),
                "rationale": f"Set {record.name} movement from {record.movement} to {movement}",
            }
        )

    if fuel_turn_limit is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-fuel-turn-limit",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x43,
                "expected": _signed_byte_hex(
                    record.fuel_turn_limit,
                    label="current fuel/turn limit",
                ),
                "replacement": _signed_byte_hex(fuel_turn_limit, label="fuel/turn limit"),
                "rationale": (
                    f"Set {record.name} fuel/turn limit from "
                    f"{record.fuel_turn_limit} to {fuel_turn_limit}"
                ),
            }
        )

    if production_cost is not None:
        if production_cost % 5 != 0:
            raise ValueError("production cost must be a multiple of 5 resources")
        quanta = production_cost // 5
        patches.append(
            {
                "id": f"unit-{record.index:03d}-production-cost",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x44,
                "expected": _signed_byte_hex(
                    record.production_cost_quanta,
                    label="current production cost quanta",
                ),
                "replacement": _signed_byte_hex(quanta, label="production cost quanta"),
                "rationale": (
                    f"Set {record.name} production cost from "
                    f"{record.production_cost} to {production_cost}"
                ),
            }
        )

    if unlock_technology_id is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-unlock-technology",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x4A,
                "expected": _technology_id_hex(record.unlock_technology_id),
                "replacement": _technology_id_hex(unlock_technology_id),
                "rationale": (
                    f"Set {record.name} unlock technology from "
                    f"{_technology_label(record.unlock_technology_id)} to "
                    f"{_technology_label(unlock_technology_id)}"
                ),
            }
        )

    if obsolete_technology_id_1 is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-obsolete-technology-1",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x4C,
                "expected": _technology_id_hex(record.obsolete_technology_id_1),
                "replacement": _technology_id_hex(obsolete_technology_id_1),
                "rationale": (
                    f"Set {record.name} obsolete technology 1 from "
                    f"{_technology_label(record.obsolete_technology_id_1)} to "
                    f"{_technology_label(obsolete_technology_id_1)}"
                ),
            }
        )

    if obsolete_technology_id_2 is not None:
        patches.append(
            {
                "id": f"unit-{record.index:03d}-obsolete-technology-2",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x4E,
                "expected": _technology_id_hex(record.obsolete_technology_id_2),
                "replacement": _technology_id_hex(obsolete_technology_id_2),
                "rationale": (
                    f"Set {record.name} obsolete technology 2 from "
                    f"{_technology_label(record.obsolete_technology_id_2)} to "
                    f"{_technology_label(obsolete_technology_id_2)}"
                ),
            }
        )

    return {
        "format_version": 1,
        "profile_id": profile_id,
        "patches": patches,
    }
