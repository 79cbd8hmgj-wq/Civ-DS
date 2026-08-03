#!/usr/bin/env bash
set -euo pipefail
if (($# != 3)); then echo "usage: $0 INPUT.bin RUNTIME_ADDRESS OUTPUT.elf" >&2; exit 2; fi
OBJCOPY="${LLVM_OBJCOPY:-/usr/bin/llvm-objcopy-20}"
"$OBJCOPY" -I binary -O elf32-littlearm -B arm \
  --rename-section .data=.text,alloc,load,readonly,code "$1" "$3"
cat >"$3.import.txt" <<META
language: ARM:LE:32:v5t
runtime_address: $2
source_binary: $1
apply_image_base: $2
META
