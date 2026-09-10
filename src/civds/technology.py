from __future__ import annotations

import struct
from dataclasses import dataclass

from civds.units import parse_unit_records

TECH_RECORD_SIZE = 106
TECH_RECORD_COUNT = 48
_TECH_TABLE_SIZE = TECH_RECORD_COUNT * TECH_RECORD_SIZE
_NAME_SIZE = 32
_EFFECT_SIZE = 64
_EFFECT_OFFSET = 42


@dataclass(frozen=True)
class TechnologyRecord:
    index: int
    offset: int
    name: str
    prerequisite_technology_ids: tuple[int, int, int]
    category_mask: int
    reserved_0x28: int
    effect: str


def _decode_text(slot: bytes, *, label: str) -> str:
    terminator = slot.find(b"\0")
    if terminator < 0:
        raise ValueError(f"{label} text slot is not NUL-terminated")
    raw = slot[:terminator]
    if any(byte < 0x20 or byte > 0x7E for byte in raw):
        raise ValueError(f"{label} text slot contains non-printable ASCII")
    if any(slot[terminator + 1 :]):
        raise ValueError(f"{label} text slot contains nonzero padding")
    return raw.decode("ascii")


def _encode_text(text: str, *, size: int, label: str) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= size:
        raise ValueError(f"{label} must be shorter than {size} bytes")
    return encoded + b"\0" * (size - len(encoded))


def _technology_table_offset(blob: bytes) -> int:
    """Locate the technology table using the already-anchor-verified unit table.

    The technology table is stored immediately before the unit descriptor
    table (`Settlers` anchor, `UNIT_RECORD_SIZE`-strided) in the confirmed
    supported-ROM layout, so its start is derived relative to that anchor
    instead of a second, independent string search.
    """
    settlers_offset = parse_unit_records(blob)[0].offset
    tech_start = settlers_offset - _TECH_TABLE_SIZE
    if tech_start < 0:
        raise ValueError("technology table would start before the beginning of the blob")
    return tech_start


def parse_technology_records(blob: bytes) -> tuple[TechnologyRecord, ...]:
    start = _technology_table_offset(blob)

    records: list[TechnologyRecord] = []
    for index in range(TECH_RECORD_COUNT):
        offset = start + index * TECH_RECORD_SIZE
        raw = blob[offset : offset + TECH_RECORD_SIZE]
        if len(raw) != TECH_RECORD_SIZE:
            raise ValueError(f"technology record {index} is truncated")

        name = _decode_text(raw[0:_NAME_SIZE], label=f"technology {index} name")
        dep0, dep1, dep2, category_mask, reserved_0x28 = struct.unpack_from(
            "<hhhhh", raw, _NAME_SIZE
        )
        effect = _decode_text(
            raw[_EFFECT_OFFSET : _EFFECT_OFFSET + _EFFECT_SIZE],
            label=f"technology {index} effect",
        )

        records.append(
            TechnologyRecord(
                index=index,
                offset=offset,
                name=name,
                prerequisite_technology_ids=(dep0, dep1, dep2),
                category_mask=category_mask,
                reserved_0x28=reserved_0x28,
                effect=effect,
            )
        )

    return tuple(records)


def _prerequisite_hex(value: int) -> str:
    return struct.pack("<h", value).hex()


def build_technology_patch_set(
    records: tuple[TechnologyRecord, ...],
    *,
    technology_name: str,
    profile_id: str,
    prerequisite_technology_ids: tuple[int | None, int | None, int | None] = (
        None,
        None,
        None,
    ),
    effect: str | None = None,
) -> dict[str, object]:
    matches = [record for record in records if record.name == technology_name]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one technology named {technology_name!r}, found {len(matches)}"
        )
    if all(value is None for value in prerequisite_technology_ids) and effect is None:
        raise ValueError("no technology fields were requested for patching")
    record = matches[0]

    patches: list[dict[str, object]] = []
    for slot, new_value in enumerate(prerequisite_technology_ids):
        if new_value is None:
            continue
        patches.append(
            {
                "id": f"technology-{record.index:03d}-prerequisite-{slot}",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + _NAME_SIZE + slot * 2,
                "expected": _prerequisite_hex(record.prerequisite_technology_ids[slot]),
                "replacement": _prerequisite_hex(new_value),
                "rationale": (
                    f"Set {record.name} prerequisite slot {slot} from "
                    f"{record.prerequisite_technology_ids[slot]} to {new_value}"
                ),
            }
        )

    if effect is not None:
        patches.append(
            {
                "id": f"technology-{record.index:03d}-effect",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + _EFFECT_OFFSET,
                "expected": _encode_text(
                    record.effect, size=_EFFECT_SIZE, label="current effect"
                ).hex(),
                "replacement": _encode_text(effect, size=_EFFECT_SIZE, label="effect").hex(),
                "rationale": f"Set {record.name} effect text from {record.effect!r} to {effect!r}",
            }
        )

    return {
        "format_version": 1,
        "profile_id": profile_id,
        "patches": patches,
    }

