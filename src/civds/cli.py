"""Command-line interface."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Any
from .errors import CivDSError, UnsupportedROMError
from .hashing import json_text, sha256_file
from .rom import inspect
from .resources import supported_roms
from .rebuild import rebuild, verify_rebuild
from .workspace import extract_workspace


def _registry() -> dict[str, Any]:
    return supported_roms()


def _validate(path: Path) -> str:
    digest = sha256_file(path)
    if digest not in _registry()["roms"]:
        raise UnsupportedROMError(f"unsupported ROM SHA-256: {digest}")
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civds")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-rom", "inspect-rom", "list-files", "list-overlays"):
        p = sub.add_parser(name)
        p.add_argument("path", type=Path)
        p.add_argument("--allow-unsupported", action="store_true")
    extract_parser = sub.add_parser("extract")
    extract_parser.add_argument("rom", type=Path)
    extract_parser.add_argument("workspace", type=Path)
    extract_parser.add_argument("--force", action="store_true")
    rebuild_parser = sub.add_parser("rebuild")
    rebuild_parser.add_argument("workspace", type=Path)
    rebuild_parser.add_argument("output", type=Path)
    verify_parser = sub.add_parser("verify-rebuild")
    verify_parser.add_argument("original", type=Path)
    verify_parser.add_argument("rebuilt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            _validate(args.rom)
            sys.stdout.write(json_text(extract_workspace(args.rom, args.workspace, args.force)))
            return 0
        if args.command == "rebuild":
            sys.stdout.write(json_text(rebuild(args.workspace, args.output)))
            return 0
        if args.command == "verify-rebuild":
            sys.stdout.write(json_text(verify_rebuild(args.original, args.rebuilt)))
            return 0
        path: Path = args.path
        digest = sha256_file(path) if args.allow_unsupported else _validate(path)
        if args.command == "validate-rom":
            value: object = {"sha256": digest, "supported": digest in _registry()["roms"]}
        else:
            header, files, overlays = inspect(path)
            value = (
                header | {"sha256": digest}
                if args.command == "inspect-rom"
                else (files if args.command == "list-files" else overlays)
            )
        sys.stdout.write(json_text(value))
        return 0
    except (CivDSError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
