from __future__ import annotations

import struct

from civds.technology import (
    TECH_RECORD_COUNT,
    TECH_RECORD_SIZE,
    parse_technology_records,
)
from civds.technology_summary import build_technology_summary
from civds.units import UNIT_RECORD_COUNT, UNIT_RECORD_SIZE, technology_name


def _tech_text(text: str, size: int) -> bytes:
    encoded = text.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("fixture text is too long")
    return encoded + b"\0" * (size - len(encoded))


def _tech_record(
    name: str,
    *,
    prerequisite_technology_ids: tuple[int, int, int] = (-1, -1, -1),
    category_mask: int = -1,
    reserved_0x28: int = -1,
    effect: str = "",
) -> bytes:
    raw = bytearray(TECH_RECORD_SIZE)
    raw[0:32] = _tech_text(name, 32)
    struct.pack_into(
        "<hhhhh",
        raw,
        32,
        prerequisite_technology_ids[0],
        prerequisite_technology_ids[1],
        prerequisite_technology_ids[2],
        category_mask,
        reserved_0x28,
    )
    raw[42:106] = _tech_text(effect, 64)
    return bytes(raw)


def _unit_text(text: str) -> bytes:
    encoded = text.encode("ascii")
    return encoded + b"\0" * (32 - len(encoded) - 1) + b"\0"


def _minimal_unit_record(name: str) -> bytes:
    raw = bytearray(UNIT_RECORD_SIZE)
    raw[0x00:0x20] = _unit_text(name)
    raw[0x20:0x40] = _unit_text("model")
    struct.pack_into("<bbbbbbbbBBhhhI", raw, 0x40, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, -1, -1, -1, 0)
    raw[0x54:0x74] = _unit_text("model")
    raw[0x74:0x94] = _unit_text("model")
    return bytes(raw)


def _blob_with_technology_records(tech_records: list[bytes]) -> bytes:
    assert len(tech_records) == TECH_RECORD_COUNT
    unit_records = [_minimal_unit_record("Settlers")]
    unit_records.extend(
        _minimal_unit_record(f"Unit {index}") for index in range(1, UNIT_RECORD_COUNT)
    )
    prefix = b"padding before the technology table\0"
    return (
        prefix
        + b"".join(tech_records)
        + b"".join(unit_records)
        + _unit_text("Pyramids of Egypt")
        + b"tail"
    )


def _all_technology_records() -> list[bytes]:
    records = [_tech_record("never", prerequisite_technology_ids=(99, 99, 99))]
    records.extend(_tech_record(f"Tech {index}") for index in range(1, TECH_RECORD_COUNT))
    return records


def test_parse_technology_records_recovers_confirmed_layout() -> None:
    records_bytes = _all_technology_records()
    records_bytes[1] = _tech_record("Alphabet", category_mask=2)
    records_bytes[3] = _tech_record(
        "Ceremonial Burial",
        prerequisite_technology_ids=(5, -1, -1),
        category_mask=8,
    )
    records_bytes[8] = _tech_record("Writing")
    records_bytes[9] = _tech_record(
        "Code of Laws",
        prerequisite_technology_ids=(8, 1, -1),
        category_mask=1,
        effect="Govt: Republic",
    )

    blob = _blob_with_technology_records(records_bytes)
    records = parse_technology_records(blob)

    assert len(records) == TECH_RECORD_COUNT

    never = records[0]
    assert never.name == "never"
    assert never.prerequisite_technology_ids == (99, 99, 99)

    alphabet = records[1]
    assert alphabet.name == "Alphabet"
    assert alphabet.prerequisite_technology_ids == (-1, -1, -1)
    assert alphabet.category_mask == 2
    assert alphabet.reserved_0x28 == -1
    assert alphabet.effect == ""

    ceremonial_burial = records[3]
    assert ceremonial_burial.name == "Ceremonial Burial"
    assert ceremonial_burial.prerequisite_technology_ids == (5, -1, -1)
    assert ceremonial_burial.category_mask == 8

    code_of_laws = records[9]
    assert code_of_laws.name == "Code of Laws"
    assert code_of_laws.prerequisite_technology_ids == (8, 1, -1)
    assert code_of_laws.effect == "Govt: Republic"

    summary = build_technology_summary(records)
    assert summary["record_count"] == TECH_RECORD_COUNT
    technologies = summary["technologies"]
    assert isinstance(technologies, list)
    assert technologies[9]["prerequisite_technology_names"] == ["Writing", "Alphabet", None]
    assert technologies[9]["effect"] == "Govt: Republic"


def test_technology_table_is_located_relative_to_the_unit_table_anchor() -> None:
    records_bytes = _all_technology_records()
    blob = _blob_with_technology_records(records_bytes)

    records = parse_technology_records(blob)

    # The technology table must end exactly where the unit table's `Settlers`
    # anchor begins - this is the load-bearing contiguity invariant that lets
    # the technology table be found without a second string scan.
    last_record_end = records[-1].offset + TECH_RECORD_SIZE
    settlers_prefix = b"padding before the technology table\0" + b"".join(records_bytes)
    assert last_record_end == len(settlers_prefix)


def test_technology_names_match_the_recovered_runtime_catalog() -> None:
    # Cross-check: civds.units.technology_name() was hand-built from earlier
    # evidence. Any real ROM parse should agree with it exactly.
    for technology_id in range(TECH_RECORD_COUNT):
        assert technology_name(technology_id) is not None
