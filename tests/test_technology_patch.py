from __future__ import annotations

import pytest

from civds.technology import build_technology_patch_set, parse_technology_records
from tests.test_technology import (
    _all_technology_records,
    _blob_with_technology_records,
    _tech_record,
)


def _records():
    records_bytes = _all_technology_records()
    records_bytes[8] = _tech_record("Writing")
    records_bytes[9] = _tech_record(
        "Code of Laws",
        prerequisite_technology_ids=(8, 1, -1),
        effect="",
    )
    blob = _blob_with_technology_records(records_bytes)
    return parse_technology_records(blob)


def test_build_technology_patch_set_rewires_a_prerequisite_slot() -> None:
    records = _records()

    patch_set = build_technology_patch_set(
        records,
        technology_name="Code of Laws",
        profile_id="civrev-usa",
        prerequisite_technology_ids=(None, 5, None),
    )

    assert patch_set["profile_id"] == "civrev-usa"
    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["target"] == "arm9"
    assert patch["offset"] == records[9].offset + 32 + 1 * 2
    assert patch["expected"] == "0100"  # little-endian int16(1) = Alphabet
    assert patch["replacement"] == "0500"  # little-endian int16(5) = Pottery


def test_build_technology_patch_set_rewrites_effect_text() -> None:
    records = _records()

    patch_set = build_technology_patch_set(
        records,
        technology_name="Code of Laws",
        profile_id="civrev-usa",
        effect="Govt: Republic",
    )

    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["offset"] == records[9].offset + 42
    assert bytes.fromhex(patch["expected"]) == b"\0" * 64
    assert bytes.fromhex(patch["replacement"]).startswith(b"Govt: Republic\0")


def test_build_technology_patch_set_requires_exactly_one_match() -> None:
    records = _records()

    with pytest.raises(ValueError, match="expected exactly one technology"):
        build_technology_patch_set(
            records,
            technology_name="Unknown Technology",
            profile_id="civrev-usa",
            effect="x",
        )


def test_build_technology_patch_set_requires_at_least_one_field() -> None:
    records = _records()

    with pytest.raises(ValueError, match="no technology fields"):
        build_technology_patch_set(
            records,
            technology_name="Code of Laws",
            profile_id="civrev-usa",
        )
