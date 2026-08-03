#!/usr/bin/env bash
set -euo pipefail
if (($# < 1)); then echo "usage: $0 ROM [DeSmuME arguments...]" >&2; exit 2; fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EMU="${CIVDS_DESMUME_DIR:-$ROOT/local/emulator/unpacked/desmume-debug}"
export LD_LIBRARY_PATH="$EMU/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"
exec timeout --signal=TERM --kill-after=2s "${CIVDS_TIMEOUT:-30s}" "$EMU/desmume-cli" --disable-sound --nojoy --3d-render SW "$@"
