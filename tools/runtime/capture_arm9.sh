#!/usr/bin/env bash
set -euo pipefail
if (($# != 2)); then echo "usage: $0 ROM OUTPUT.json" >&2; exit 2; fi
port="${CIVDS_GDB_PORT:-3333}"; log="${2%.json}.emulator.log"
cleanup(){ [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null || true; wait "${pid:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
tools/runtime/launch.sh "$1" --arm9gdb "$port" >"$log" 2>&1 & pid=$!
python tools/gdb_remote.py --port "$port" --output "$2"
