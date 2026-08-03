"""Transactional, immutable-original extraction workspace."""

from __future__ import annotations
from dataclasses import asdict
from pathlib import Path, PurePosixPath
import os
import shutil
import tempfile
from typing import BinaryIO
from .compression.blz import decompress as decompress_blz
from .compression.lz10 import decompress as decompress_lz10, is_lz10
from .errors import CivDSError, FormatError
from .fat import parse_fat
from .fnt import parse_fnt
from .hashing import json_text, sha256_file
from .nds_header import read_header
from .overlays import Overlay, parse_overlays
from .rom import BANNER_EXTENTS


def _slice(stream: BinaryIO, offset: int, size: int) -> bytes:
    stream.seek(offset)
    value = stream.read(size)
    if len(value) != size:
        raise FormatError("short ROM read")
    return value


def _safe(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise CivDSError(f"unsafe workspace path: {relative}")
    target = root.joinpath(*parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise CivDSError(f"workspace path escapes root: {relative}")
    return target


def extract_workspace(rom: Path, workspace: Path, force: bool = False) -> dict[str, object]:
    if workspace.exists() and any(workspace.iterdir()) and not force:
        raise CivDSError(f"workspace is populated: {workspace}")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{workspace.name}.", dir=workspace.parent))
    try:
        for name in ("original", "decoded", "modified", "rebuilt", "reports", "runtime"):
            (temporary / name).mkdir()
        header = read_header(rom)
        with rom.open("rb") as stream:
            fat = parse_fat(_slice(stream, header.fat.rom_offset, header.fat.size), header.rom_size)
            names = {
                item.file_id: item.path
                for item in parse_fnt(
                    _slice(stream, header.fnt.rom_offset, header.fnt.size), len(fat)
                )
            }
            extents = [item.end - item.start for item in fat]
            overlays: list[tuple[str, Overlay]] = []
            for processor, table in (
                ("arm9", header.arm9_overlay_table),
                ("arm7", header.arm7_overlay_table),
            ):
                table_data = _slice(stream, table.rom_offset, table.size)
                overlays.extend((processor, item) for item in parse_overlays(table_data, extents))
            overlay_ids = {item.file_id: (processor, item) for processor, item in overlays}
            manifest_files: list[dict[str, object]] = []
            for entry in fat:
                payload = _slice(stream, entry.start, entry.end - entry.start)
                relative = f"fat/{entry.file_id:04d}.bin"
                target = _safe(temporary / "original", relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                compression = "none"
                decoded = payload
                overlay = overlay_ids.get(entry.file_id)
                if overlay and overlay[1].is_compressed:
                    decoded = decompress_blz(payload)
                    compression = "blz"
                elif is_lz10(payload):
                    # 0x10 is common in arbitrary resources. A stream is identified
                    # only when its complete structural decode succeeds.
                    try:
                        decoded = decompress_lz10(payload)
                        compression = "lz10"
                    except FormatError:
                        decoded = payload
                decoded_target = _safe(temporary / "decoded", relative)
                decoded_target.parent.mkdir(parents=True, exist_ok=True)
                decoded_target.write_bytes(decoded)
                nitrofs_name = names.get(entry.file_id)
                if nitrofs_name is not None and overlay is None:
                    named_original = _safe(temporary / "original" / "nitrofs", nitrofs_name)
                    named_decoded = _safe(temporary / "decoded" / "nitrofs", nitrofs_name)
                    named_original.parent.mkdir(parents=True, exist_ok=True)
                    named_decoded.parent.mkdir(parents=True, exist_ok=True)
                    os.link(target, named_original)
                    os.link(decoded_target, named_decoded)
                if overlay is not None:
                    overlay_name = f"{overlay[0]}_{overlay[1].overlay_id:04d}.bin"
                    overlay_original = temporary / "original" / "overlays" / overlay_name
                    overlay_decoded = temporary / "decoded" / "overlays" / overlay_name
                    overlay_original.parent.mkdir(parents=True, exist_ok=True)
                    overlay_decoded.parent.mkdir(parents=True, exist_ok=True)
                    os.link(target, overlay_original)
                    os.link(decoded_target, overlay_decoded)
                manifest_files.append(
                    {
                        "file_id": entry.file_id,
                        "nitrofs_path": nitrofs_name,
                        "rom_offset": entry.start,
                        "stored_size": len(payload),
                        "stored_sha256": sha256_file(target),
                        "decoded_size": len(decoded),
                        "decoded_sha256": sha256_file(decoded_target),
                        "compression": compression,
                        "overlay_id": overlay[1].overlay_id if overlay else None,
                        "processor": overlay[0] if overlay else None,
                    }
                )
            for name, program in (("arm9", header.arm9), ("arm7", header.arm7)):
                target = temporary / "original" / f"{name}.bin"
                target.write_bytes(_slice(stream, program.rom_offset, program.size))
            banner_version = int.from_bytes(_slice(stream, header.banner_offset, 2), "little")
            try:
                banner_extent = BANNER_EXTENTS[banner_version]
            except KeyError as exc:
                raise FormatError(f"unsupported banner version 0x{banner_version:x}") from exc
            (temporary / "original" / "banner.bin").write_bytes(
                _slice(stream, header.banner_offset, banner_extent)
            )
        shutil.copyfile(rom, temporary / "original" / "rom.nds")
        manifest = {
            "schema_version": 1,
            "rom_sha256": sha256_file(rom),
            "rom_size": header.rom_size,
            "header": header.to_dict(),
            "files": manifest_files,
            "overlays": [{"processor": processor, **asdict(item)} for processor, item in overlays],
        }
        (temporary / "reports" / "extraction.json").write_text(
            json_text(manifest), encoding="utf-8"
        )
        for path in (temporary / "original").rglob("*"):
            if path.is_file():
                path.chmod(0o444)
        if workspace.exists():
            shutil.rmtree(workspace)
        os.replace(temporary, workspace)
        return manifest
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
