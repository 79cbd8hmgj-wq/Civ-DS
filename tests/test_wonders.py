from __future__ import annotations

import struct

from civds.wonders import (
    WONDER_RECORD_COUNT,
    WONDER_RECORD_SIZE,
    parse_wonder_records,
)
from civds.wonders_summary import build_wonder_summary


def _text(text: str, size: int) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("fixture text is too long")
    return encoded + b"\0" * (size - len(encoded))


def _wonder_record(
    name: str,
    *,
    production_cost_quanta: int = 0,
    unknown_0x42: int = 0,
    prerequisite_technology_id: int = -1,
    unknown_0x46: int = -1,
    unknown_0x48: int = 0,
    short_name: str = "",
    model_name: str = "",
    description: str = "",
    unknown_0x14a: int = 0,
) -> bytes:
    raw = bytearray(WONDER_RECORD_SIZE)
    raw[0x00:0x20] = _text(name, 32)
    struct.pack_into("<h", raw, 0x40, production_cost_quanta)
    struct.pack_into("<h", raw, 0x42, unknown_0x42)
    struct.pack_into("<h", raw, 0x44, prerequisite_technology_id)
    struct.pack_into("<h", raw, 0x46, unknown_0x46)
    struct.pack_into("<h", raw, 0x48, unknown_0x48)
    raw[0x4A:0x8A] = _text(short_name, 64)
    raw[0x8A:0xCA] = _text(model_name, 64)
    raw[0xCA:0x14A] = _text(description, 0x14A - 0xCA)
    struct.pack_into("<h", raw, 0x14A, unknown_0x14a)
    return bytes(raw)


def _all_wonder_records() -> list[bytes]:
    records = [_wonder_record(f"Wonder {index}") for index in range(WONDER_RECORD_COUNT)]
    records[0] = _wonder_record(
        "Pyramids of Egypt",
        production_cost_quanta=30,
        unknown_0x42=8,
        prerequisite_technology_id=3,
        short_name="Pyramid",
        model_name="Pyramid_anc",
        description="all forms of government are available.",
    )
    return records


def _blob_with_wonder_records(records: list[bytes] | None = None) -> bytes:
    records = records if records is not None else _all_wonder_records()
    assert len(records) == WONDER_RECORD_COUNT
    return b"padding before the wonder table" + b"".join(records) + b"tail"


def test_parse_wonder_records_recovers_confirmed_layout() -> None:
    records_bytes = _all_wonder_records()
    records_bytes[4] = _wonder_record(
        "Colossus of Rhodes",
        production_cost_quanta=20,
        unknown_0x42=4,
        prerequisite_technology_id=2,
        short_name="Colossus",
        model_name="Pyramid_anc",
        description="trade will be doubled in this city.",
    )
    records_bytes[3] = _wonder_record(
        "Stonehenge",
        production_cost_quanta=10,
        prerequisite_technology_id=-1,
        short_name="Stonehenge",
        model_name="Pyramid_anc",
        description="our Temples will be 50% more effective.",
    )
    blob = _blob_with_wonder_records(records_bytes)

    records = parse_wonder_records(blob)

    assert len(records) == WONDER_RECORD_COUNT

    pyramids = records[0]
    assert pyramids.name == "Pyramids of Egypt"
    assert pyramids.production_cost_quanta == 30
    assert pyramids.production_cost == 150
    assert pyramids.prerequisite_technology_id == 3
    assert pyramids.short_name == "Pyramid"
    assert pyramids.model_name == "Pyramid_anc"
    assert pyramids.description == "all forms of government are available."

    colossus = records[4]
    assert colossus.name == "Colossus of Rhodes"
    assert colossus.prerequisite_technology_id == 2

    stonehenge = records[3]
    assert stonehenge.name == "Stonehenge"
    assert stonehenge.prerequisite_technology_id == -1

    summary = build_wonder_summary(records)
    assert summary["record_count"] == WONDER_RECORD_COUNT
    wonders = summary["wonders"]
    assert isinstance(wonders, list)
    assert wonders[0]["production_cost"] == 150
    assert wonders[0]["prerequisite_technology_name"] == "Ceremonial Burial"
    assert wonders[3]["prerequisite_technology_name"] is None
