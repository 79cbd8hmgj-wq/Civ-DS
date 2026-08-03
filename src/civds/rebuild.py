"""Deterministic same-layout rebuilding and no-change verification."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, cast
from .errors import CivDSError
from .hashing import json_text, sha256_file


def rebuild(workspace: Path, output: Path) -> dict[str, object]:
    manifest_path = workspace / "reports" / "extraction.json"
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    source = workspace / "original" / "rom.nds"
    if sha256_file(source) != manifest["rom_sha256"]:
        raise CivDSError("immutable source ROM hash differs from extraction manifest")
    data = bytearray(source.read_bytes())
    changed: list[int] = []
    for row in manifest["files"]:
        file_id = int(row["file_id"])
        modified = workspace / "modified" / "fat" / f"{file_id:04d}.bin"
        if not modified.exists():
            continue
        payload = modified.read_bytes()
        if len(payload) != int(row["stored_size"]):
            raise CivDSError(f"file {file_id} size change requires relocation and is refused")
        offset = int(row["rom_offset"])
        original = workspace / "original" / "fat" / f"{file_id:04d}.bin"
        if sha256_file(original) != row["stored_sha256"]:
            raise CivDSError(f"file {file_id} immutable original hash differs")
        data[offset : offset + len(payload)] = payload
        changed.append(file_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_bytes(data)
    temporary.replace(output)
    report = {
        "changed_file_ids": changed,
        "output_sha256": sha256_file(output),
        "source_sha256": manifest["rom_sha256"],
        "byte_identical": not changed and sha256_file(output) == manifest["rom_sha256"],
    }
    report_path = workspace / "reports" / "rebuild.json"
    report_path.write_text(json_text(report), encoding="utf-8")
    return report


def verify_rebuild(original: Path, rebuilt: Path) -> dict[str, object]:
    result = {
        "original_sha256": sha256_file(original),
        "rebuilt_sha256": sha256_file(rebuilt),
        "byte_identical": False,
        "first_difference": None,
    }
    if original.stat().st_size != rebuilt.stat().st_size:
        result["size_difference"] = rebuilt.stat().st_size - original.stat().st_size
        return result
    with original.open("rb") as left, rebuilt.open("rb") as right:
        offset = 0
        while True:
            a, b = left.read(1024 * 1024), right.read(1024 * 1024)
            if not a:
                result["byte_identical"] = True
                return result
            if a != b:
                result["first_difference"] = offset + next(
                    index for index, pair in enumerate(zip(a, b)) if pair[0] != pair[1]
                )
                return result
            offset += len(a)
