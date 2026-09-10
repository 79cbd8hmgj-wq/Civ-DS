from __future__ import annotations

import struct
from dataclasses import dataclass

CIVILIZATION_COUNT = 16
_LEADER_NAME_ANCHOR = b"Caesar\0"


@dataclass(frozen=True)
class CivilizationRecord:
    index: int
    leader_name: str
    leader_name_offset: int
    leader_name_capacity: int


def _unique_offset(blob: bytes, needle: bytes, label: str) -> int:
    first = blob.find(needle)
    if first < 0:
        raise ValueError(f"{label} anchor not found")
    if blob.find(needle, first + 1) >= 0:
        raise ValueError(f"{label} anchor is not unique")
    return first


def _decode_cstring(blob: bytes, offset: int, *, label: str) -> tuple[str, int]:
    terminator = blob.find(b"\0", offset)
    if terminator < 0:
        raise ValueError(f"{label} is not NUL-terminated")
    raw = blob[offset:terminator]
    if any(byte < 0x20 or byte > 0x7E for byte in raw):
        raise ValueError(f"{label} contains non-printable ASCII")

    capacity_end = terminator + 1
    while capacity_end < len(blob) and blob[capacity_end] == 0:
        capacity_end += 1

    return raw.decode("ascii"), capacity_end - offset


def parse_civilization_records(
    blob: bytes, *, arm9_ram_address: int
) -> tuple[CivilizationRecord, ...]:
    """Recover the 16-entry leader-name pointer table.

    The table is located relative to the `Caesar\\0` leader-name string
    (a unique anchor, civilization id 0 / Rome): that string's ARM9-relative
    offset is converted to an absolute RAM address and the resulting 4-byte
    value is located as the unique pointer-array slot for civilization 0,
    from which the remaining 15 civilizations follow at a 4-byte stride.
    """
    caesar_offset = _unique_offset(blob, _LEADER_NAME_ANCHOR, "Caesar leader name")
    caesar_address = arm9_ram_address + caesar_offset

    pointer_needle = struct.pack("<I", caesar_address)
    table_start = _unique_offset(blob, pointer_needle, "civilization 0 leader-name pointer")

    records: list[CivilizationRecord] = []
    for index in range(CIVILIZATION_COUNT):
        pointer_offset = table_start + index * 4
        raw_pointer = blob[pointer_offset : pointer_offset + 4]
        if len(raw_pointer) != 4:
            raise ValueError(f"civilization {index} leader-name pointer is truncated")
        (pointer_address,) = struct.unpack("<I", raw_pointer)

        name_offset = pointer_address - arm9_ram_address
        if not 0 <= name_offset < len(blob):
            raise ValueError(
                f"civilization {index} leader-name pointer targets outside the ARM9 image"
            )

        leader_name, capacity = _decode_cstring(
            blob, name_offset, label=f"civilization {index} leader name"
        )
        records.append(
            CivilizationRecord(
                index=index,
                leader_name=leader_name,
                leader_name_offset=name_offset,
                leader_name_capacity=capacity,
            )
        )

    return tuple(records)


def _encode_leader_name(name: str, *, capacity: int, label: str) -> bytes:
    encoded = name.encode("ascii")
    if len(encoded) >= capacity:
        raise ValueError(
            f"{label} must be shorter than {capacity} bytes (the original packed "
            "string pool leaves no room for a longer name without disturbing the "
            "next string)"
        )
    return encoded + b"\0" * (capacity - len(encoded))


def build_civilization_patch_set(
    records: tuple[CivilizationRecord, ...],
    *,
    leader_name: str,
    profile_id: str,
    new_leader_name: str,
) -> dict[str, object]:
    matches = [record for record in records if record.leader_name == leader_name]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one civilization with leader name {leader_name!r}, "
            f"found {len(matches)}"
        )
    record = matches[0]

    original_bytes = _encode_leader_name(
        record.leader_name, capacity=record.leader_name_capacity, label="current leader name"
    )
    replacement_bytes = _encode_leader_name(
        new_leader_name, capacity=record.leader_name_capacity, label="leader name"
    )

    patches = [
        {
            "id": f"civilization-{record.index:03d}-leader-name",
            "type": "binary_replace",
            "target": "arm9",
            "offset": record.leader_name_offset,
            "expected": original_bytes.hex(),
            "replacement": replacement_bytes.hex(),
            "rationale": (
                f"Set civilization {record.index} leader name from "
                f"{record.leader_name!r} to {new_leader_name!r}"
            ),
        }
    ]

    return {
        "format_version": 1,
        "profile_id": profile_id,
        "patches": patches,
    }
