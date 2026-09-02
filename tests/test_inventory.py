from __future__ import annotations

import json
from pathlib import Path

from civds.cli import main
from civds.inventory import summarize_inventory, write_inventory_summary


def _files_payload() -> dict[str, object]:
    return {
        "files": [
            {
                "file_id": 17,
                "path": "Version.Txt",
                "decoded_size": 9,
                "compression": "none",
            },
            {
                "file_id": 18,
                "path": "advisors/CulturalAdvisor.NCGR",
                "decoded_size": 43056,
                "compression": "none",
            },
            {
                "file_id": 19,
                "path": "data/GameRules.DAT",
                "decoded_size": 1024,
                "compression": "lz10",
            },
            {
                "file_id": 20,
                "path": "scripts/bootstrap",
                "decoded_size": 64,
                "compression": "none",
            },
        ]
    }


def _assets_payload() -> dict[str, object]:
    return {
        "assets": [
            {
                "file_id": 17,
                "path": "Version.Txt",
                "detected_format": None,
                "evidence": "unknown",
            },
            {
                "file_id": 18,
                "path": "advisors/CulturalAdvisor.NCGR",
                "detected_format": "NCGR",
                "evidence": "signature",
            },
            {
                "file_id": 19,
                "path": "data/GameRules.DAT",
                "detected_format": None,
                "evidence": "unknown",
            },
            {
                "file_id": 20,
                "path": "scripts/bootstrap",
                "detected_format": None,
                "evidence": "unknown",
            },
        ]
    }


def test_summarize_inventory_groups_paths_and_formats_deterministically() -> None:
    summary = summarize_inventory(_files_payload(), _assets_payload(), rare_extension_limit=2)

    assert summary["totals"] == {
        "files": 4,
        "assets": 4,
        "decoded_bytes": 44153,
        "top_level_directories": 4,
        "extensions": 4,
    }
    assert summary["top_level_directories"] == [
        {"directory": "<root>", "count": 1, "decoded_bytes": 9},
        {"directory": "advisors", "count": 1, "decoded_bytes": 43056},
        {"directory": "data", "count": 1, "decoded_bytes": 1024},
        {"directory": "scripts", "count": 1, "decoded_bytes": 64},
    ]
    assert summary["compression"] == [
        {"name": "none", "count": 3},
        {"name": "lz10", "count": 1},
    ]
    assert summary["detected_formats"] == [
        {"name": "unknown", "count": 3},
        {"name": "NCGR", "count": 1},
    ]
    assert summary["unknown_extensions"] == [
        {"extension": ".dat", "count": 1, "example_paths": ["data/GameRules.DAT"]},
        {"extension": ".txt", "count": 1, "example_paths": ["Version.Txt"]},
        {"extension": "<none>", "count": 1, "example_paths": ["scripts/bootstrap"]},
    ]
    assert summary["largest_files"][0]["path"] == "advisors/CulturalAdvisor.NCGR"
    assert {row["extension"] for row in summary["rare_extensions"]} == {
        ".dat",
        ".ncgr",
        ".txt",
        "<none>",
    }


def test_write_inventory_summary_is_deterministic(tmp_path: Path) -> None:
    files = tmp_path / "files.json"
    assets = tmp_path / "assets.json"
    output = tmp_path / "nested" / "summary.json"
    files.write_text(json.dumps(_files_payload()), encoding="utf-8")
    assets.write_text(json.dumps(_assets_payload()), encoding="utf-8")

    write_inventory_summary(files, assets, output)
    first = output.read_bytes()
    write_inventory_summary(files, assets, output)

    assert output.read_bytes() == first
    assert first.endswith(b"\n")


def test_inventory_cli_writes_summary(tmp_path: Path) -> None:
    files = tmp_path / "files.json"
    assets = tmp_path / "assets.json"
    output = tmp_path / "summary.json"
    files.write_text(json.dumps(_files_payload()), encoding="utf-8")
    assets.write_text(json.dumps(_assets_payload()), encoding="utf-8")

    result = main(
        [
            "inventory",
            "summarize",
            str(files),
            str(assets),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8"))["totals"]["files"] == 4
