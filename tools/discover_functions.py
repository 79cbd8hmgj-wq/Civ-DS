#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from civds.analysis.arm import report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("binary", type=Path)
    p.add_argument("base", type=lambda x: int(x, 0))
    p.add_argument("output", type=Path)
    p.add_argument("--start", type=lambda x: int(x, 0), default=0)
    a = p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report(a.binary.read_bytes(), a.base, a.start), indent=2, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
