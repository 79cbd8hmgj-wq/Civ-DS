#!/usr/bin/env bash
set -euo pipefail
if (($# < 3 || $# > 5)); then echo "usage: $0 INPUT.bin RUNTIME_ADDRESS OUTPUT.txt [START_OFFSET [STOP_OFFSET]]" >&2; exit 2; fi
OBJDUMP="${LLVM_OBJDUMP:-/usr/lib/llvm-20/bin/llvm-objdump}"
tmp="$(mktemp --suffix=.elf)"; trap 'rm -f "$tmp"' EXIT
tools/prepare_raw_elf.sh "$1" "$2" "$tmp"
args=(-D -j .text --triple=armv5te-none-eabi "--adjust-vma=$2")
[[ $# -ge 4 ]] && args+=("--start-address=$4")
[[ $# -ge 5 ]] && args+=("--stop-address=$5")
"$OBJDUMP" "${args[@]}" "$tmp" >"$3"
