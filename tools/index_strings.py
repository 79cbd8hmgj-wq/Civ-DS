#!/usr/bin/env python3
"""Create a local JSONL executable/resource string index without committing text."""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from civds.string_table import parse_stbl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = json.loads((args.workspace / "reports/extraction.json").read_text())
    rows = []
    for item in report["files"]:
        path = args.workspace / "original/fat" / f"{item['file_id']:04d}.bin"
        data = path.read_bytes()
        if data[:4] == b"STBL":
            for record in parse_stbl(data):
                rows.append(
                    {
                        "component": f"fat_{item['file_id']:04d}",
                        "file_id": item["file_id"],
                        "offset": record.data_offset,
                        "key_hash": f"0x{record.key_hash:08x}",
                        "text_sha256": hashlib.sha256(record.text.encode()).hexdigest(),
                        "text": record.text,
                    }
                )
    for component, path, base in [("arm9", args.workspace / "original/arm9.bin", 0x02000000)]:
        data = path.read_bytes()
        start = None
        for pos, byte in enumerate(data + b"\0"):
            if 0x20 <= byte < 0x7F:
                start = pos if start is None else start
            elif start is not None:
                if pos - start >= 4:
                    raw = data[start:pos]
                    rows.append(
                        {
                            "component": component,
                            "offset": start,
                            "runtime_address": base + start,
                            "text_sha256": hashlib.sha256(raw).hexdigest(),
                            "text": raw.decode("ascii"),
                        }
                    )
                start = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
