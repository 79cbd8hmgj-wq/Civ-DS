from __future__ import annotations

import struct
from dataclasses import dataclass

WONDER_RECORD_SIZE = 0x14C
WONDER_RECORD_COUNT = 21
_NAME_SIZE = 32
_SHORT_NAME_OFFSET = 0x4A
_SHORT_NAME_SIZE = 64
_MODEL_NAME_OFFSET = 0x8A
_MODEL_NAME_SIZE = 64
_DESCRIPTION_OFFSET = 0xCA
_DESCRIPTION_SIZE = 0x14A - _DESCRIPTION_OFFSET
_START_ANCHOR = b"Pyramids of Egypt\0"


@dataclass(frozen=True)
class WonderRecord:
    index: int
    offset: int
    name: str
    production_cost_quanta: int
    unknown_0x42: int
    prerequisite_technology_id: int
    unknown_0x46: int
    unknown_0x48: int
    short_name: str
    model_name: str
    description: str
    unknown_0x14a: int

    @property
    def production_cost(self) -> int:
        return self.production_cost_quanta * 5


def _unique_offset(blob: bytes, needle: bytes, label: str) -> int:
    first = blob.find(needle)
    if first < 0:
        raise ValueError(f"{label} anchor not found")
    if blob.find(needle, first + 1) >= 0:
        raise ValueError(f"{label} anchor is not unique")
    return first


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


def parse_wonder_records(blob: bytes) -> tuple[WonderRecord, ...]:
    """Recover the 21-entry wonder descriptor table.

    Located via the `Pyramids of Egypt\\0` name anchor - the same string
    already load-bearing as the unit table's own end-of-table boundary
    check (`civds.units`), since the wonder table begins immediately where
    the unit table ends with no gap. Stride (0x14C / 332 bytes) and record
    count (21) are cross-validated by the runtime availability-check loop
    (a sibling of the building-table loop, bound `0x15` = 21) - see
    analysis/buildings-model.md.

    Only fields backed by proven or strongly-supported evidence get
    semantic names; the rest stay `unknown_0xNN` per the same evidence bar
    already applied to the building table.
    """
    start = _unique_offset(blob, _START_ANCHOR, "Pyramids of Egypt wonder name")

    records: list[WonderRecord] = []
    for index in range(WONDER_RECORD_COUNT):
        offset = start + index * WONDER_RECORD_SIZE
        raw = blob[offset : offset + WONDER_RECORD_SIZE]
        if len(raw) != WONDER_RECORD_SIZE:
            raise ValueError(f"wonder record {index} is truncated")

        name = _decode_text(raw[0:_NAME_SIZE], label=f"wonder {index} name")
        (production_cost_quanta,) = struct.unpack_from("<h", raw, 0x40)
        (unknown_0x42,) = struct.unpack_from("<h", raw, 0x42)
        (prerequisite_technology_id,) = struct.unpack_from("<h", raw, 0x44)
        (unknown_0x46,) = struct.unpack_from("<h", raw, 0x46)
        (unknown_0x48,) = struct.unpack_from("<h", raw, 0x48)
        short_name = _decode_text(
            raw[_SHORT_NAME_OFFSET : _SHORT_NAME_OFFSET + _SHORT_NAME_SIZE],
            label=f"wonder {index} short name",
        )
        model_name = _decode_text(
            raw[_MODEL_NAME_OFFSET : _MODEL_NAME_OFFSET + _MODEL_NAME_SIZE],
            label=f"wonder {index} model name",
        )
        description = _decode_text(
            raw[_DESCRIPTION_OFFSET : _DESCRIPTION_OFFSET + _DESCRIPTION_SIZE],
            label=f"wonder {index} description",
        )
        (unknown_0x14a,) = struct.unpack_from("<h", raw, 0x14A)

        records.append(
            WonderRecord(
                index=index,
                offset=offset,
                name=name,
                production_cost_quanta=production_cost_quanta,
                unknown_0x42=unknown_0x42,
                prerequisite_technology_id=prerequisite_technology_id,
                unknown_0x46=unknown_0x46,
                unknown_0x48=unknown_0x48,
                short_name=short_name,
                model_name=model_name,
                description=description,
                unknown_0x14a=unknown_0x14a,
            )
        )

    return tuple(records)


def _prerequisite_hex(value: int) -> str:
    return struct.pack("<h", value).hex()


def _quanta_hex(value: int) -> str:
    return struct.pack("<h", value).hex()


def build_wonder_patch_set(
    records: tuple[WonderRecord, ...],
    *,
    wonder_name: str,
    profile_id: str,
    production_cost: int | None = None,
    prerequisite_technology_id: int | None = None,
    description: str | None = None,
) -> dict[str, object]:
    matches = [record for record in records if record.name == wonder_name]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one wonder named {wonder_name!r}, found {len(matches)}")
    if all(value is None for value in (production_cost, prerequisite_technology_id, description)):
        raise ValueError("no wonder fields were requested for patching")
    record = matches[0]

    patches: list[dict[str, object]] = []

    if production_cost is not None:
        if production_cost % 5 != 0:
            raise ValueError("production cost must be a multiple of 5 resources")
        quanta = production_cost // 5
        patches.append(
            {
                "id": f"wonder-{record.index:03d}-production-cost",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x40,
                "expected": _quanta_hex(record.production_cost_quanta),
                "replacement": _quanta_hex(quanta),
                "rationale": (
                    f"Set {record.name} production cost from "
                    f"{record.production_cost} to {production_cost}"
                ),
            }
        )

    if prerequisite_technology_id is not None:
        patches.append(
            {
                "id": f"wonder-{record.index:03d}-prerequisite-technology",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x44,
                "expected": _prerequisite_hex(record.prerequisite_technology_id),
                "replacement": _prerequisite_hex(prerequisite_technology_id),
                "rationale": (
                    f"Set {record.name} prerequisite technology from "
                    f"{record.prerequisite_technology_id} to {prerequisite_technology_id}"
                ),
            }
        )

    if description is not None:
        patches.append(
            {
                "id": f"wonder-{record.index:03d}-description",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + _DESCRIPTION_OFFSET,
                "expected": _encode_text(
                    record.description, size=_DESCRIPTION_SIZE, label="current description"
                ).hex(),
                "replacement": _encode_text(
                    description, size=_DESCRIPTION_SIZE, label="description"
                ).hex(),
                "rationale": (
                    f"Set {record.name} description from {record.description!r} "
                    f"to {description!r}"
                ),
            }
        )

    return {
        "format_version": 1,
        "profile_id": profile_id,
        "patches": patches,
    }
