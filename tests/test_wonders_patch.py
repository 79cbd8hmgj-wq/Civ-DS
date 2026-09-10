from __future__ import annotations

import pytest

from civds.wonders import build_wonder_patch_set, parse_wonder_records
from tests.test_wonders import _all_wonder_records, _blob_with_wonder_records, _wonder_record


def _records():
    records_bytes = _all_wonder_records()
    records_bytes[0] = _wonder_record(
        "Pyramids of Egypt",
        production_cost_quanta=30,
        prerequisite_technology_id=3,
        short_name="Pyramid",
        model_name="Pyramid_anc",
        description="all forms of government are available.",
    )
    blob = _blob_with_wonder_records(records_bytes)
    return parse_wonder_records(blob)


def test_build_wonder_patch_set_changes_production_cost() -> None:
    records = _records()

    patch_set = build_wonder_patch_set(
        records,
        wonder_name="Pyramids of Egypt",
        profile_id="civrev-usa",
        production_cost=200,
    )

    assert patch_set["profile_id"] == "civrev-usa"
    patches = patch_set["patches"]
    assert len(patches) == 1
    patch = patches[0]
    assert patch["target"] == "arm9"
    assert patch["offset"] == records[0].offset + 0x40
    assert patch["expected"] == "1e00"
    assert patch["replacement"] == "2800"


def test_build_wonder_patch_set_changes_prerequisite_technology() -> None:
    records = _records()

    patch_set = build_wonder_patch_set(
        records,
        wonder_name="Pyramids of Egypt",
        profile_id="civrev-usa",
        prerequisite_technology_id=5,
    )

    patch = patch_set["patches"][0]
    assert patch["offset"] == records[0].offset + 0x44
    assert patch["expected"] == "0300"
    assert patch["replacement"] == "0500"


def test_build_wonder_patch_set_changes_description() -> None:
    records = _records()

    patch_set = build_wonder_patch_set(
        records,
        wonder_name="Pyramids of Egypt",
        profile_id="civrev-usa",
        description="all forms of government are cheaper.",
    )

    patch = patch_set["patches"][0]
    assert patch["offset"] == records[0].offset + 0xCA
    assert bytes.fromhex(patch["replacement"]).startswith(b"all forms of government are cheaper.\0")


def test_build_wonder_patch_set_rejects_production_cost_not_multiple_of_five() -> None:
    records = _records()

    with pytest.raises(ValueError, match="multiple of 5"):
        build_wonder_patch_set(
            records, wonder_name="Pyramids of Egypt", profile_id="civrev-usa", production_cost=101
        )


def test_build_wonder_patch_set_requires_exactly_one_match() -> None:
    records = _records()

    with pytest.raises(ValueError, match="expected exactly one wonder"):
        build_wonder_patch_set(
            records, wonder_name="Unknown Wonder", profile_id="civrev-usa", production_cost=10
        )


def test_build_wonder_patch_set_requires_at_least_one_field() -> None:
    records = _records()

    with pytest.raises(ValueError, match="no wonder fields"):
        build_wonder_patch_set(records, wonder_name="Pyramids of Egypt", profile_id="civrev-usa")
