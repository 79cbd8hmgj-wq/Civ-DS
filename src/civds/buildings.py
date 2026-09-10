from __future__ import annotations

import struct
from dataclasses import dataclass

BUILDING_RECORD_SIZE = 0xCC
BUILDING_RECORD_COUNT = 24
_NAME_SIZE = 32
_MODEL_NAME_SIZE = 32
_DESCRIPTION_OFFSET = 0x4C
_DESCRIPTION_SIZE = BUILDING_RECORD_SIZE - _DESCRIPTION_OFFSET
_START_ANCHOR = b"Palace\0"
_LAST_RECORD_NAME = "never"


@dataclass(frozen=True)
class BuildingRecord:
    index: int
    offset: int
    name: str
    model_name: str
    unknown_0x40: int
    production_cost_quanta: int
    prerequisite_technology_id: int
    requires_building_mask: int
    excludes_building_mask: int
    description: str

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


def _decode_text_lenient(slot: bytes, *, label: str) -> str:
    """Like `_decode_text`, but falls back to `""` instead of raising.

    Used only for the table's known sentinel record (index
    `BUILDING_RECORD_COUNT - 1`, name `never`), which the runtime
    availability-check loop never iterates over (it stops at index 22) and
    whose non-name bytes are not a validly NUL-padded string in the
    supported ROM (observed content is small-integer/`-1` sentinel-looking
    junk, not text) - see analysis/buildings-model.md.
    """
    try:
        return _decode_text(slot, label=label)
    except ValueError:
        return ""


def _encode_text(text: str, *, size: int, label: str) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= size:
        raise ValueError(f"{label} must be shorter than {size} bytes")
    return encoded + b"\0" * (size - len(encoded))


def parse_building_records(blob: bytes) -> tuple[BuildingRecord, ...]:
    """Recover the 24-entry building/improvement descriptor table.

    Located via the `Palace\\0` name anchor (a unique string in the
    supported ROM, record index 0). Record boundaries and stride (0xCC /
    204 bytes) are cross-validated by requiring the table to end exactly
    on a record named `never` (index 23, a non-buildable sentinel record
    also confirmed absent from the runtime availability-check loop, which
    iterates only indices 0-22).
    """
    start = _unique_offset(blob, _START_ANCHOR, "Palace building name")

    records: list[BuildingRecord] = []
    for index in range(BUILDING_RECORD_COUNT):
        offset = start + index * BUILDING_RECORD_SIZE
        raw = blob[offset : offset + BUILDING_RECORD_SIZE]
        if len(raw) != BUILDING_RECORD_SIZE:
            raise ValueError(f"building record {index} is truncated")

        is_sentinel_record = index == BUILDING_RECORD_COUNT - 1
        decode_text = _decode_text_lenient if is_sentinel_record else _decode_text

        name = _decode_text(raw[0:_NAME_SIZE], label=f"building {index} name")
        model_name = decode_text(
            raw[_NAME_SIZE : _NAME_SIZE + _MODEL_NAME_SIZE],
            label=f"building {index} model name",
        )
        unknown_0x40 = raw[0x40]
        production_cost_quanta = raw[0x41]
        (prerequisite_technology_id,) = struct.unpack_from("<h", raw, 0x42)
        (requires_building_mask,) = struct.unpack_from("<I", raw, 0x44)
        (excludes_building_mask,) = struct.unpack_from("<I", raw, 0x48)
        description = decode_text(
            raw[_DESCRIPTION_OFFSET : _DESCRIPTION_OFFSET + _DESCRIPTION_SIZE],
            label=f"building {index} description",
        )

        records.append(
            BuildingRecord(
                index=index,
                offset=offset,
                name=name,
                model_name=model_name,
                unknown_0x40=unknown_0x40,
                production_cost_quanta=production_cost_quanta,
                prerequisite_technology_id=prerequisite_technology_id,
                requires_building_mask=requires_building_mask,
                excludes_building_mask=excludes_building_mask,
                description=description,
            )
        )

    if records[-1].name != _LAST_RECORD_NAME:
        raise ValueError(
            f"building table boundary check failed: record {BUILDING_RECORD_COUNT - 1} "
            f"is named {records[-1].name!r}, expected {_LAST_RECORD_NAME!r}"
        )

    return tuple(records)


def _byte_hex(value: int, *, label: str) -> str:
    if not 0 <= value <= 255:
        raise ValueError(f"{label} must fit in a byte (0..255)")
    return struct.pack("<B", value).hex()


def _prerequisite_hex(value: int) -> str:
    return struct.pack("<h", value).hex()


def _mask_hex(value: int, *, label: str) -> str:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{label} must fit in a 32-bit unsigned word")
    return struct.pack("<I", value).hex()


def build_building_patch_set(
    records: tuple[BuildingRecord, ...],
    *,
    building_name: str,
    profile_id: str,
    production_cost: int | None = None,
    prerequisite_technology_id: int | None = None,
    requires_building_mask: int | None = None,
    excludes_building_mask: int | None = None,
    description: str | None = None,
) -> dict[str, object]:
    matches = [record for record in records if record.name == building_name]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one building named {building_name!r}, found {len(matches)}"
        )
    if all(
        value is None
        for value in (
            production_cost,
            prerequisite_technology_id,
            requires_building_mask,
            excludes_building_mask,
            description,
        )
    ):
        raise ValueError("no building fields were requested for patching")
    record = matches[0]

    patches: list[dict[str, object]] = []

    if production_cost is not None:
        if production_cost % 5 != 0:
            raise ValueError("production cost must be a multiple of 5 resources")
        quanta = production_cost // 5
        patches.append(
            {
                "id": f"building-{record.index:03d}-production-cost",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x41,
                "expected": _byte_hex(
                    record.production_cost_quanta, label="current production cost quanta"
                ),
                "replacement": _byte_hex(quanta, label="production cost quanta"),
                "rationale": (
                    f"Set {record.name} production cost from "
                    f"{record.production_cost} to {production_cost}"
                ),
            }
        )

    if prerequisite_technology_id is not None:
        patches.append(
            {
                "id": f"building-{record.index:03d}-prerequisite-technology",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x42,
                "expected": _prerequisite_hex(record.prerequisite_technology_id),
                "replacement": _prerequisite_hex(prerequisite_technology_id),
                "rationale": (
                    f"Set {record.name} prerequisite technology from "
                    f"{record.prerequisite_technology_id} to {prerequisite_technology_id}"
                ),
            }
        )

    if requires_building_mask is not None:
        patches.append(
            {
                "id": f"building-{record.index:03d}-requires-building-mask",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x44,
                "expected": _mask_hex(
                    record.requires_building_mask, label="current requires-building mask"
                ),
                "replacement": _mask_hex(
                    requires_building_mask, label="requires-building mask"
                ),
                "rationale": (
                    f"Set {record.name} requires-building mask from "
                    f"{record.requires_building_mask:#010x} to {requires_building_mask:#010x}"
                ),
            }
        )

    if excludes_building_mask is not None:
        patches.append(
            {
                "id": f"building-{record.index:03d}-excludes-building-mask",
                "type": "binary_replace",
                "target": "arm9",
                "offset": record.offset + 0x48,
                "expected": _mask_hex(
                    record.excludes_building_mask, label="current excludes-building mask"
                ),
                "replacement": _mask_hex(
                    excludes_building_mask, label="excludes-building mask"
                ),
                "rationale": (
                    f"Set {record.name} excludes-building mask from "
                    f"{record.excludes_building_mask:#010x} to {excludes_building_mask:#010x}"
                ),
            }
        )

    if description is not None:
        patches.append(
            {
                "id": f"building-{record.index:03d}-description",
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
