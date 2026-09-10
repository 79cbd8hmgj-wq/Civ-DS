from __future__ import annotations

import struct

import pytest

from civds.buildings import (
    BUILDING_RECORD_COUNT,
    BUILDING_RECORD_SIZE,
    parse_building_records,
)
from civds.buildings_summary import build_building_summary


def _text(text: str, size: int) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("fixture text is too long")
    return encoded + b"\0" * (size - len(encoded))


def _building_record(
    name: str,
    *,
    model_name: str = "",
    unknown_0x40: int = 0,
    production_cost_quanta: int = 0,
    prerequisite_technology_id: int = 0,
    requires_building_mask: int = 0,
    excludes_building_mask: int = 0,
    description: str = "",
) -> bytes:
    raw = bytearray(BUILDING_RECORD_SIZE)
    raw[0x00:0x20] = _text(name, 32)
    raw[0x20:0x40] = _text(model_name, 32)
    raw[0x40] = unknown_0x40 & 0xFF
    raw[0x41] = production_cost_quanta & 0xFF
    struct.pack_into("<h", raw, 0x42, prerequisite_technology_id)
    struct.pack_into("<I", raw, 0x44, requires_building_mask)
    struct.pack_into("<I", raw, 0x48, excludes_building_mask)
    raw[0x4C : BUILDING_RECORD_SIZE] = _text(description, BUILDING_RECORD_SIZE - 0x4C)
    return bytes(raw)


def _all_building_records() -> list[bytes]:
    records = [_building_record(f"Building {index}") for index in range(BUILDING_RECORD_COUNT)]
    records[0] = _building_record("Palace", model_name="Palace_anc")
    records[23] = _building_record("never")
    return records


def _blob_with_building_records(records: list[bytes] | None = None) -> bytes:
    records = records if records is not None else _all_building_records()
    assert len(records) == BUILDING_RECORD_COUNT
    return b"padding before the building table\0" + b"".join(records) + b"tail"


def test_parse_building_records_recovers_confirmed_layout() -> None:
    records_bytes = _all_building_records()
    records_bytes[10] = _building_record(
        "Bank",
        model_name="Bank",
        production_cost_quanta=12,
        prerequisite_technology_id=20,
        requires_building_mask=1 << 4,
        description="4x city gold production",
    )
    records_bytes[3] = _building_record(
        "Temple",
        production_cost_quanta=4,
        prerequisite_technology_id=3,
        excludes_building_mask=1 << 11,
        description="+1 happiness per citizen",
    )
    blob = _blob_with_building_records(records_bytes)

    records = parse_building_records(blob)

    assert len(records) == BUILDING_RECORD_COUNT

    palace = records[0]
    assert palace.name == "Palace"
    assert palace.model_name == "Palace_anc"

    bank = records[10]
    assert bank.name == "Bank"
    assert bank.production_cost_quanta == 12
    assert bank.production_cost == 60
    assert bank.prerequisite_technology_id == 20
    assert bank.requires_building_mask == 1 << 4
    assert bank.excludes_building_mask == 0
    assert bank.description == "4x city gold production"

    temple = records[3]
    assert temple.name == "Temple"
    assert temple.prerequisite_technology_id == 3
    assert temple.excludes_building_mask == 1 << 11

    last = records[23]
    assert last.name == "never"

    summary = build_building_summary(records)
    assert summary["record_count"] == BUILDING_RECORD_COUNT
    buildings = summary["buildings"]
    assert isinstance(buildings, list)
    assert buildings[10]["production_cost"] == 60
    assert buildings[10]["prerequisite_technology_name"] == "Banking"


def test_sentinel_record_with_non_text_padding_does_not_crash_the_parser() -> None:
    # The real ROM's index-23 "never" sentinel record carries non-text
    # junk (not zero-padded ASCII) in its model-name/description bytes -
    # this record is never reached by the runtime availability-check loop
    # (which stops at index 22), so parsing must tolerate it rather than
    # raising on strict text validation.
    records_bytes = _all_building_records()
    raw = bytearray(_building_record("never"))
    raw[0x20:0x2A] = bytes([0x63, 0x00, 0x63, 0x00, 0x63, 0x00, 0xFF, 0xFF, 0xFF, 0xFF])
    records_bytes[23] = bytes(raw)
    blob = _blob_with_building_records(records_bytes)

    records = parse_building_records(blob)

    assert records[23].name == "never"
    assert records[23].model_name == ""


def test_building_table_boundary_is_validated() -> None:
    records_bytes = _all_building_records()
    records_bytes[23] = _building_record("not never")
    blob = _blob_with_building_records(records_bytes)

    with pytest.raises(ValueError, match="never"):
        parse_building_records(blob)
