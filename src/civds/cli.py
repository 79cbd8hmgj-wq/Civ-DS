"""Command-line interface."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast
from .errors import CivDSError, UnsupportedROMError
from .hashing import json_text, sha256_file
from .rom import inspect


def _registry() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path("config/supported_roms.json").read_text()))


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
    args = parser.parse_args(argv)
    path: Path = args.path
    try:
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
