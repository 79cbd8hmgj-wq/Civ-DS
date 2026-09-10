from __future__ import annotations

import pytest

from civds.buildings import build_building_patch_set, parse_building_records
from tests.test_buildings import (
    _all_building_records,
    _blob_with_building_records,
    _building_record,
)


def _records():
    records_bytes = _all_building_records()
    records_bytes[10] = _building_record(
        "Bank",
        production_cost_quanta=12,
        prerequisite_technology_id=20,
        requires_building_mask=1 << 4,
        excludes_building_mask=0,
        description="4x city gold production",
    )
    blob = _blob_with_building_records(records_bytes)
    return parse_building_records(blob)


def test_build_building_patch_set_changes_production_cost() -> None:
    records = _records()

    patch_set = build_building_patch_set(
        records,
        building_name="Bank",
        profile_id="civrev-usa",
        production_cost=100,
    )

    assert patch_set["profile_id"] == "civrev-usa"
    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["target"] == "arm9"
    assert patch["offset"] == records[10].offset + 0x41
    assert patch["expected"] == "0c"
    assert patch["replacement"] == "14"


def test_build_building_patch_set_changes_prerequisite_technology() -> None:
    records = _records()

    patch_set = build_building_patch_set(
        records,
        building_name="Bank",
        profile_id="civrev-usa",
        prerequisite_technology_id=14,
    )

    patch = patch_set["patches"][0]
    assert patch["offset"] == records[10].offset + 0x42
    assert patch["expected"] == "1400"
    assert patch["replacement"] == "0e00"


def test_build_building_patch_set_changes_requires_and_excludes_masks() -> None:
    records = _records()

    patch_set = build_building_patch_set(
        records,
        building_name="Bank",
        profile_id="civrev-usa",
        requires_building_mask=0,
        excludes_building_mask=1 << 10,
    )

    patches = {p["id"]: p for p in patch_set["patches"]}
    assert len(patches) == 2
    requires = patches["building-010-requires-building-mask"]
    assert requires["offset"] == records[10].offset + 0x44
    assert requires["expected"] == "10000000"
    assert requires["replacement"] == "00000000"
    excludes = patches["building-010-excludes-building-mask"]
    assert excludes["offset"] == records[10].offset + 0x48
    assert excludes["expected"] == "00000000"
    assert excludes["replacement"] == "00040000"


def test_build_building_patch_set_changes_description() -> None:
    records = _records()

    patch_set = build_building_patch_set(
        records,
        building_name="Bank",
        profile_id="civrev-usa",
        description="6x city gold production",
    )

    patch = patch_set["patches"][0]
    assert patch["offset"] == records[10].offset + 0x4C
    assert bytes.fromhex(patch["replacement"]).startswith(b"6x city gold production\0")


def test_build_building_patch_set_rejects_production_cost_not_multiple_of_five() -> None:
    records = _records()

    with pytest.raises(ValueError, match="multiple of 5"):
        build_building_patch_set(
            records, building_name="Bank", profile_id="civrev-usa", production_cost=61
        )


def test_build_building_patch_set_requires_exactly_one_match() -> None:
    records = _records()

    with pytest.raises(ValueError, match="expected exactly one building"):
        build_building_patch_set(
            records, building_name="Unknown Building", profile_id="civrev-usa", production_cost=10
        )


def test_build_building_patch_set_requires_at_least_one_field() -> None:
    records = _records()

    with pytest.raises(ValueError, match="no building fields"):
        build_building_patch_set(records, building_name="Bank", profile_id="civrev-usa")
