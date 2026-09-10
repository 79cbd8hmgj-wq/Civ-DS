from __future__ import annotations

import struct

import pytest

from civds.civilization import (
    CIVILIZATION_COUNT,
    build_civilization_patch_set,
    parse_civilization_records,
)
from civds.civilization_summary import build_civilization_summary

ARM9_RAM_ADDRESS = 0x02000000

_LEADER_NAMES = [
    "Caesar",
    "Cleopatra",
    "Alexander",
    "Isabella",
    "Bismarck",
    "Catherine",
    "Mao",
    "Lincoln",
    "Tokugawa",
    "Napoleon",
    "Gandhi",
    "Saladin",
    "Montezuma",
    "Shaka",
    "Genghis",
    "Elizabeth",
]


def _packed_string_pool(names: list[str]) -> tuple[bytes, list[int]]:
    """Pack names back-to-back, NUL-terminated, 4-byte aligned - matching the
    real ROM's leader-name string pool layout."""
    pool = bytearray()
    offsets = []
    for name in names:
        offsets.append(len(pool))
        pool.extend(name.encode("ascii"))
        pool.append(0)
        while len(pool) % 4 != 0:
            pool.append(0)
    return bytes(pool), offsets


def _blob_with_civilization_table(names: list[str] | None = None) -> bytes:
    names = list(names) if names is not None else list(_LEADER_NAMES)
    assert len(names) == CIVILIZATION_COUNT

    prefix = b"\xff" * 0x100
    pool, pool_offsets = _packed_string_pool(names)
    pool_start = len(prefix)

    pointer_table = b"".join(
        struct.pack("<I", ARM9_RAM_ADDRESS + pool_start + offset) for offset in pool_offsets
    )
    filler = b"\xff" * 0x40

    return prefix + pool + filler + pointer_table + b"\xff" * 0x20


def test_parse_civilization_records_recovers_the_leader_name_table() -> None:
    blob = _blob_with_civilization_table()

    records = parse_civilization_records(blob, arm9_ram_address=ARM9_RAM_ADDRESS)

    assert len(records) == CIVILIZATION_COUNT
    assert [record.leader_name for record in records] == _LEADER_NAMES
    assert records[0].index == 0
    assert records[-1].leader_name == "Elizabeth"

    summary = build_civilization_summary(records)
    assert summary["record_count"] == CIVILIZATION_COUNT
    assert summary["civilizations"][9]["leader_name"] == "Napoleon"


def test_leader_name_capacity_matches_the_packed_string_pool_gap() -> None:
    blob = _blob_with_civilization_table()
    records = parse_civilization_records(blob, arm9_ram_address=ARM9_RAM_ADDRESS)

    # "Caesar\0" is 7 bytes, padded to an 8-byte aligned slot.
    caesar = records[0]
    assert caesar.leader_name == "Caesar"
    assert caesar.leader_name_capacity == 8

    # "Mao\0" is 4 bytes, already aligned - zero padding bytes.
    mao = records[6]
    assert mao.leader_name == "Mao"
    assert mao.leader_name_capacity == 4


def test_build_civilization_patch_set_renames_a_leader_in_place() -> None:
    blob = _blob_with_civilization_table()
    records = parse_civilization_records(blob, arm9_ram_address=ARM9_RAM_ADDRESS)

    patch_set = build_civilization_patch_set(
        records,
        leader_name="Napoleon",
        profile_id="civrev-usa",
        new_leader_name="Louis",
    )

    assert patch_set["profile_id"] == "civrev-usa"
    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["target"] == "arm9"
    assert patch["offset"] == records[9].leader_name_offset
    assert bytes.fromhex(patch["expected"]) == b"Napoleon\0\0\0\0"
    assert bytes.fromhex(patch["replacement"]) == b"Louis\0\0\0\0\0\0\0"


def test_build_civilization_patch_set_rejects_a_name_too_long_for_the_slot() -> None:
    blob = _blob_with_civilization_table()
    records = parse_civilization_records(blob, arm9_ram_address=ARM9_RAM_ADDRESS)

    with pytest.raises(ValueError, match="must be shorter than"):
        build_civilization_patch_set(
            records,
            leader_name="Mao",
            profile_id="civrev-usa",
            new_leader_name="Napoleon Bonaparte",
        )


def test_build_civilization_patch_set_requires_exactly_one_match() -> None:
    blob = _blob_with_civilization_table()
    records = parse_civilization_records(blob, arm9_ram_address=ARM9_RAM_ADDRESS)

    with pytest.raises(ValueError, match="expected exactly one civilization"):
        build_civilization_patch_set(
            records,
            leader_name="Unknown Leader",
            profile_id="civrev-usa",
            new_leader_name="X",
        )
