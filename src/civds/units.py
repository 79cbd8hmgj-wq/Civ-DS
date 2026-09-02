from __future__ import annotations

import struct
from dataclasses import dataclass

UNIT_RECORD_SIZE = 0x94
UNIT_RECORD_COUNT = 38
_UNIT_START_ANCHOR = b"Settlers\0"
_UNIT_END_ANCHOR = b"Pyramids of Egypt\0"


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
    unknown_0x43: int
    unknown_0x44: int
    unknown_0x45: int
    unknown_0x46: int
    unknown_0x47: int
    formation_count: int
    unlock_technology_id: int
    obsolete_technology_id_1: int
    obsolete_technology_id_2: int
    flags: int


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
            unknown_0x43,
            unknown_0x44,
            unknown_0x45,
            unknown_0x46,
            unknown_0x47,
            formation_count,
            unlock_technology_id,
            obsolete_technology_id_1,
            obsolete_technology_id_2,
            flags,
        ) = struct.unpack_from("<bbbbbbbbHhhhI", raw, 0x40)

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
                unknown_0x43=unknown_0x43,
                unknown_0x44=unknown_0x44,
                unknown_0x45=unknown_0x45,
                unknown_0x46=unknown_0x46,
                unknown_0x47=unknown_0x47,
                formation_count=formation_count,
                unlock_technology_id=unlock_technology_id,
                obsolete_technology_id_1=obsolete_technology_id_1,
                obsolete_technology_id_2=obsolete_technology_id_2,
                flags=flags,
            )
        )

    return tuple(records)
